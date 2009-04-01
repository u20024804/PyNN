"""
Unit tests for all simulators
$Id:$
"""

import sys
import unittest
import numpy
import os
from pyNN import common, random

def assert_arrays_almost_equal(a, b, threshold):
    if not (abs(a-b) < threshold).all():
        err_msg = "%s != %s" % (a, b)
        err_msg += "\nlargest difference = %g" % abs(a-b).max()
        raise unittest.TestCase.failureException(err_msg)

# ==============================================================================
class IDSetGetTest(unittest.TestCase):
    """Tests of the ID.__setattr__()`, `ID.__getattr()` `ID.setParameters()`
    and `ID.getParameters()` methods for all available standard cell types
    and for both lone and in-population IDs."""
    
    model_list = []
    default_dp = 5
    decimal_places = {'duration': 2, 'start': 2}
        
    def setUp(self):
        sim.setup()
        self.cells = {}
        self.populations = {}
        if not IDSetGetTest.model_list:
            IDSetGetTest.model_list = sim.list_standard_models()
        for cell_class in IDSetGetTest.model_list:
            self.cells[cell_class.__name__] = sim.create(cell_class, n=2)
            self.populations[cell_class.__name__] = sim.Population(2, cell_class)
    
    def tearDown(self):
        pass
    
    def testSetGet(self):
        """__setattr__(), __getattr__(): sanity check"""
        for cell_class in IDSetGetTest.model_list:
            cell_list = (self.cells[cell_class.__name__][0],
                         self.populations[cell_class.__name__][0])
            parameter_names = cell_class.default_parameters.keys()
            for cell in cell_list:
                for name in parameter_names:
                    if name == 'spike_times':
                        i = [1.0, 2.0]
                        cell.__setattr__(name, i)
                        o = list(cell.__getattr__(name))
                        self.assertEqual(i, o)
                    else:
                        if name == 'v_thresh':
                            if 'v_spike' in parameter_names:
                                i = (cell.__getattr__('v_spike') + max(cell.__getattr__('v_reset'), cell.__getattr__('v_init')))/2
                            elif 'v_init' in parameter_names:
                                i = max(cell.__getattr__('v_reset'), cell.__getattr__('v_init')) + numpy.random.uniform(0.1, 100)
                            else:
                                i = cell.__getattr__('v_reset') + numpy.random.uniform(0.1, 100)
                        elif name == 'v_reset' or name == 'v_init': # v_reset must be less than v_thresh
                            if hasattr(cell, 'v_thresh'):
                                i = cell.__getattr__('v_thresh') - numpy.random.uniform(0.1, 100)
                            else:
                                i = numpy.random.uniform(0.1, 100)
                        elif name == 'v_spike': # v_spike must be greater than v_thresh
                            i = cell.__getattr__('v_thresh') + numpy.random.uniform(0.1, 100)
                        else:
                            i = numpy.random.uniform(0.1, 100) # tau_refrac is always at least dt (=0.1)
                        try:
                            cell.__setattr__(name, i)
                        except Exception, e:
                            raise Exception("%s. %s=%g in %s with %s" % (e, name, i, cell_class, cell.get_parameters()))
                        o = cell.__getattr__(name)
                        self.assertEqual(type(i), type(o), "%s: input: %s, output: %s" % (name, type(i), type(o)))
                        self.assertAlmostEqual(i, o,
                                               IDSetGetTest.decimal_places.get(name, IDSetGetTest.default_dp),
                                               "%s in %s: %s != %s" % (name, cell_class.__name__, i,o))
    
    def testSetGetParameters(self):
        """setParameters(), getParameters(): sanity check"""
        # need to add similar test for native models in the sim-specific test files
        default_dp = 6
        decimal_places = {'duration': 2, 'start': 2}
        for cell_class in IDSetGetTest.model_list:
            cell_list = (self.cells[cell_class.__name__][0],
                         self.populations[cell_class.__name__][0])
            parameter_names = cell_class.default_parameters.keys()
            if 'v_thresh' in parameter_names: # make sure 'v_thresh' comes first
                parameter_names.remove('v_thresh')
                parameter_names = ['v_thresh'] + parameter_names
            for cell in cell_list:
                new_parameters = {}
                for name in parameter_names:
                    if name == 'spike_times':
                        new_parameters[name] = [1.0, 2.0]
                    elif name == 'v_thresh':
                        new_parameters[name] = numpy.random.uniform(-100, 100)
                    elif name == 'v_reset' or name == 'v_init':
                        if 'v_thresh' in parameter_names:
                            new_parameters[name] = new_parameters['v_thresh'] - numpy.random.uniform(0.1, 100)
                        else:
                            new_parameters[name] = numpy.random.uniform(0.1, 100)
                    elif name == 'v_spike':
                        new_parameters[name] = new_parameters['v_thresh'] + numpy.random.uniform(0.1, 100)
                    else:
                        new_parameters[name] = numpy.random.uniform(0.1, 100) # tau_refrac is always at least dt (=0.1)
                try:
                    cell.set_parameters(**new_parameters)
                except Exception, e:
                    raise Exception("%s. %s in %s" % (e, new_parameters, cell_class))
                retrieved_parameters = cell.get_parameters()
                self.assertEqual(set(new_parameters.keys()), set(retrieved_parameters.keys()))
                
                for name in new_parameters:
                    i = new_parameters[name]; o = retrieved_parameters[name]
                    if name != 'spike_times':
                        self.assertEqual(type(i), type(o), "%s: input: %s, output: %s" % (name, type(i), type(o)))
                        self.assertAlmostEqual(i, o,
                                               IDSetGetTest.decimal_places.get(name, IDSetGetTest.default_dp),
                                               "%s in %s: %s != %s" % (name, cell_class.__name__, i,o))
    
    def testGetCellClass(self):
        assert 'cellclass' in common.IDMixin.non_parameter_attributes
        for name, pop in self.populations.items():
            assert isinstance(pop[0], common.IDMixin)
            assert 'cellclass' in pop[0].non_parameter_attributes
            self.assertEqual(pop[0].cellclass.__name__, name)
        self.assertRaises(Exception, setattr, pop[0].cellclass, 'dummy')
        
    def testGetSetPosition(self):
        for cell_group in self.cells.values():
            pos = cell_group[0].position
            self.assertEqual(len(pos), 3)
            cell_group[0].position = (9.8, 7.6, 5.4)
            self.assertEqual(tuple(cell_group[0].position), (9.8, 7.6, 5.4))
       
class PopulationSpikesTest(unittest.TestCase):
    
    def setUp(self):
        sim.setup()
        self.spiketimes = numpy.arange(5,105,10.0)
        spiketimes_2D = self.spiketimes.reshape((len(self.spiketimes),1))
        self.input_spike_array = numpy.concatenate((numpy.zeros(spiketimes_2D.shape, 'float'), spiketimes_2D),
                                                   axis=1)
        self.p1 = sim.Population(1, sim.SpikeSourceArray, {'spike_times': self.spiketimes})
    
    def tearDown(self):
        pass
    
    def testGetSpikes(self):
        self.p1.record()
        sim.run(100.0)
        output_spike_array = self.p1.getSpikes()
        assert_arrays_almost_equal(self.input_spike_array, output_spike_array, 1e-11)
    
    def testPopulationRecordTwice(self):
        """Neurons should not be recorded twice.
        Multiple calls to `Population.record()` are ok, but a given neuron will only be
        recorded once."""
        self.p1.record()
        self.p1.record()
        sim.run(100.0)
        output_spike_array = self.p1.getSpikes()
        self.assertEqual(self.input_spike_array.shape, (10,2))
        self.assertEqual(self.input_spike_array.shape, output_spike_array.shape)

class PopulationSetTest(unittest.TestCase):
    
    def setUp(self):
        sim.setup()
        cell_params = {
            'tau_m' : 20.,  'tau_syn_E' : 2.3,   'tau_syn_I': 4.5,
            'v_rest': -55., 'v_reset'   : -62.3, 'v_thresh' : -50.2,
            'cm'    : 1.,   'tau_refrac': 2.3}
        self.p1 = sim.Population((5,4,3), sim.IF_curr_exp, cell_params)
        self.p2 = sim.Population((2,2), sim.SpikeSourceArray)
        
    def testSetOnlyChangesTheDesiredParameters(self):
        before = [cell.get_parameters() for cell in self.p1]
        self.p1.set('v_init', -78.9)
        after = [cell.get_parameters() for cell in self.p1]
        for name in self.p1.celltype.__class__.default_parameters:
            if name == 'v_init':
                for a in after:
                    self.assertAlmostEqual(a[name], -78.9, places=5)
            else:
                for b,a in zip(before,after):
                    self.assert_(b[name] == a[name], "%s: %s != %s" % (name, b[name], a[name]))
                
    def test_set_invalid_type(self):
        self.assertRaises(common.InvalidParameterValueError, self.p1.set, 'foo', {})
        self.assertRaises(common.InvalidParameterValueError, self.p1.set, [1,2,3])
                
    def testRandomInit(self):
        rd = random.RandomDistribution('uniform', [-75,-55])
        self.p1.randomInit(rd)
        self.assertNotEqual(self.p1[0,0,0].v_init, self.p1[0,0,1].v_init)
                
    def test_tset(self):
        tau_m = numpy.arange(10.0, 16.0, 0.1).reshape((5,4,3))
        self.p1.tset("tau_m", tau_m)
        self.assertEqual(self.p1[0,0,0].tau_m, 10.0)
        self.assertEqual(self.p1[0,0,1].tau_m, 10.1)
        self.assertAlmostEqual(self.p1[0,3,1].tau_m, 11.0, 9)
        
        spike_times = numpy.arange(40.0).reshape(2,2,10)
        self.p2.tset("spike_times", spike_times)
        self.assertEqual(list(self.p2[0,0].spike_times), numpy.arange(10.0).tolist())
        self.assertEqual(list(self.p2[1,1].spike_times), numpy.arange(30.0,40.0).tolist())
                
class PopulationPositionsTest(unittest.TestCase):
    
    def test_nearest(self):
        p = sim.Population((4,5,6), sim.IF_cond_exp)
        self.assertEqual(p.nearest((0.0,0.0,0.0)), p[0,0,0])
        self.assertEqual(p.nearest((0.0,1.0,0.0)), p[0,1,0])
        self.assertEqual(p.nearest((1.0,0.0,0.0)), p[1,0,0])
        self.assertEqual(p.nearest((3.0,2.0,1.0)), p[3,2,1])
        self.assertEqual(p.nearest((3.49,2.49,1.49)), p[3,2,1])
        self.assertEqual(p.nearest((3.49,2.49,1.51)), p[3,2,2])
        self.assertEqual(p.nearest((3.49,2.49,1.5)), p[3,2,2])
        self.assertEqual(p.nearest((2.5,2.5,1.5)), p[3,3,2])
                
class PopulationCellAccessTest(unittest.TestCase):
    
    def test_index(self):
        p = sim.Population((4,5,6), sim.IF_cond_exp)
        self.assertEqual(p.index(0), p[0,0,0])
        self.assertEqual(p.index(119), p[3,4,5])
        self.assertEqual(p.index([0,1,2]).tolist(), [p[0,0,0], p[0,0,1], p[0,0,2]])
                
class SynapticPlasticityTest(unittest.TestCase):
    
    def setUp(self):
        sim.setup()
    
    def test_ProjectionInit(self):
        for wd in (sim.AdditiveWeightDependence(),
                   sim.MultiplicativeWeightDependence(),
                   sim.AdditivePotentiationMultiplicativeDepression()):
            fast_mech = sim.TsodyksMarkramMechanism()
            slow_mech = sim.STDPMechanism(
                        timing_dependence=sim.SpikePairRule(),
                        weight_dependence=wd,
                        dendritic_delay_fraction=1.0
            )
            p1 = sim.Population(10, sim.SpikeSourceArray)
            p2 = sim.Population(10, sim.IF_cond_exp)
            prj1 = sim.Projection(p1, p2, sim.OneToOneConnector(),
                                  synapse_dynamics=sim.SynapseDynamics(fast_mech, None))
            prj2 = sim.Projection(p1, p2, sim.OneToOneConnector(),
                                  synapse_dynamics=sim.SynapseDynamics(None, slow_mech))
                
class ProjectionTest(unittest.TestCase):
    
    def setUp(self):
        sim.setup()
        p1 = sim.Population(10, sim.SpikeSourceArray)
        p2 = sim.Population(10, sim.IF_cond_exp)
        self.prj = sim.Projection(p1, p2, sim.OneToOneConnector())
        
    def test_describe(self):
        self.prj.describe()
        
    def test_printWeights(self):
        self.prj.printWeights("weights_list.tmp", format='list', gather=False)
        self.prj.printWeights("weights_array.tmp", format='array', gather=False)
        # test needs completing. Should read in the weights and check they have the correct values
         
         
class ConnectorsTest(unittest.TestCase):
    
    def test_OneToOne_with_unequal_pop_sizes(self):
        sim.setup()
        p1 = sim.Population(10, sim.SpikeSourceArray)
        p2 = sim.Population(9, sim.IF_cond_exp)
        c = sim.OneToOneConnector()
        self.assertRaises(Exception, sim.Projection, p1, p2, c) 
                
class ElectrodesTest(unittest.TestCase):
    
    def test_DCSource(self):
        # just check no Exceptions are raised, for now.
        source = sim.DCSource(amplitude=0.5, start=50.0, stop=100.0)
        cells = sim.create(sim.IF_curr_exp, {}, 5)
        source.inject_into(cells)
        for cell in cells:
            cell.inject(source)
                
    def test_StepCurrentSource(self):
        # just check no Exceptions are raised, for now.
        source = sim.StepCurrentSource([10.0, 20.0, 30.0, 40.0], [-0.1, 0.2, -0.1, 0.0])
        cells = sim.create(sim.IF_curr_exp, {}, 5)
        source.inject_into(cells)
        for cell in cells:
            cell.inject(source)
                
class StateTest(unittest.TestCase):
    
    def test_get_time(self):
        sim.setup()
        self.assertEqual(sim.get_current_time(), 0.0)
        sim.run(100.0)
        self.assertAlmostEqual(sim.get_current_time(), 100.0, 9)
        
    def test_get_time_step(self):
        sim.setup()
        self.assertEqual(sim.get_time_step(), 0.1)
        sim.setup(timestep=0.05)
        self.assertEqual(sim.get_time_step(), 0.05)
                
# ==============================================================================
if __name__ == "__main__":
    simulator = sys.argv[1]
    sys.argv.remove(simulator) # because unittest.main() processes sys.argv
    sim = __import__("pyNN.%s" % simulator, None, None, [simulator])
    unittest.main()