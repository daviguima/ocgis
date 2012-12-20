import unittest
import numpy as np
import itertools
import datetime
from shapely.geometry.point import Point
from ocgis.api.dataset.collection.collection import Identifier, OcgCollection,\
    OcgVariable
from ocgis.api.dataset.collection.iterators import KeyedIterator, MeltedIterator
from ocgis.api.dataset.collection.dimension import OcgDimension, LevelDimension,\
    SpatialDimension, TemporalDimension
import netCDF4 as nc
from ocgis.util.helpers import get_temp_path


class TestCollection(unittest.TestCase):

    def test_OcgDimension(self):
        _bounds = [None,
                  np.array([[0,100],[100,200]])]
        value = np.array([50,150])
        uid = np.arange(1,value.shape[0]+1)
        
        for bounds in _bounds:
            dim = OcgDimension(uid,value,bounds=bounds)
            self.assertEqual(dim.shape,(2,))
            for row in dim:
                pass
                    
    def test_Identifier(self):
        init_vals = np.array([50,55])
        oid = Identifier(init_vals)
        oid.add(np.array(55))
        self.assertEqual(2,len(oid))
        oid.add(np.array([55,56]))
        self.assertEqual(3,len(oid))
        self.assertEqual(3,oid.uid[-1])
        self.assertEqual(oid.get(55),2)
        oid.add(np.array([50,55,58,60]))
        self.assertEqual(len(oid),5)
        
        init_vals = np.array([datetime.datetime(2000,1,1,12),datetime.datetime(2001,12,31,12)])
        oid = Identifier(init_vals)
        self.assertEqual(2,len(oid))
        oid.add(np.array(datetime.datetime(2000,2,3)))
        self.assertEqual(3,len(oid))
        self.assertEqual(oid.get(datetime.datetime(2000,2,3)),3)
        
        init_vals = np.array([[datetime.datetime(2000,1,1,12),datetime.datetime(2001,12,31,12)],
                              [datetime.datetime(2004,1,1,12),datetime.datetime(2005,12,31,12)]])
        oid = Identifier(init_vals)
        self.assertEqual(len(oid),2)
        oid.add(np.array([[datetime.datetime(2004,1,1,12),datetime.datetime(2005,12,31,12)]]))
        self.assertEqual(len(oid),2)
        oid.add(np.array([[datetime.datetime(2008,1,1,12),datetime.datetime(2005,12,31,12)]]))
        self.assertEqual(len(oid),3)
        uid = oid.get(np.array([[datetime.datetime(2000,1,1,12),datetime.datetime(2001,12,31,12)]]))
        self.assertEqual(1,uid)
        uid = oid.get(np.array([[datetime.datetime(2008,1,1,12),datetime.datetime(2005,12,31,12)]]))
        self.assertEqual(3,uid)
        
        ## test initializing with uids
        init_vals = np.array([50,55])
        init_uids = np.array([25,26])
        oid = Identifier(init_vals,init_uids=init_uids)
        self.assertTrue((oid.uid == init_uids).all())
        oid.add(np.array([60,61]),uids=np.array([100,101]))
        self.assertEqual(oid.get(60),100)
        ## override initialized unique ids but they are not unique
        with self.assertRaises(ValueError):
            Identifier(np.array([1,2]),init_uids=np.array([55,55]))
        ## override uids, but do not provide unique values
        with self.assertRaises(ValueError):
            oid.add(np.array([60,61]),uids=np.array([101,101]))
        prev_len = len(oid)
        oid.add(np.array([60,61]),uids=np.array([100,101]))
        self.assertEqual(prev_len,len(oid))
        with self.assertRaises(ValueError):
            oid.add(62,uids=np.array([100]))
        oid.add(np.array([60,201]),uids=np.array([100,102]))
        self.assertEqual(len(oid),5)
        
#    def test_Identifier_ugid(self):
#        oid = Identifier(dtype=object)
#        x = (-123,-124)
#        y = (40,50)
#        pts = [Point(ix,iy) for ix,iy in zip(x,y)]
#        adds = np.empty((2,2),dtype=object)
#        uids = np.array([1,2])
#        
#        adds1 = adds.copy()
#        adds1[:,0] = 4
#        adds1[:,1] = pts
#        oid.add(adds1,uids)
#        
#        adds2 = adds.copy()
#        adds2[:,0] = 5
#        adds2[:,1] = pts
#        oid.add(adds2,uids)
#        import ipdb;ipdb.set_trace()
        
    def get_TemporalDimension(self,add_bounds=True):
        start = datetime.datetime(2000,1,1,12)
        end = datetime.datetime(2001,12,31,12)
        delta = datetime.timedelta(1)
        times = []
        check = start
        while check <= end:
            times.append(check)
            check += delta
        times = np.array(times)
        
        if add_bounds:
            time_bounds = []
            delta = datetime.timedelta(hours=12)
            for t in times.flat:
                time_bounds.append([t-delta,t+delta])
            time_bounds = np.array(time_bounds)
        else:
            time_bounds = None
        
        uid = np.arange(1,times.shape[0]+1)
        tdim = TemporalDimension(uid,times,bounds=time_bounds)
        
        return(tdim)
    
    def get_hourly_TemporalDimension(self,add_bounds=True):
        start = datetime.datetime(2000,1,1,0,30)
        end = datetime.datetime(2001,12,31,23,30)
        delta = datetime.timedelta(hours=1)
        times = []
        check = start
        while check <= end:
            times.append(check)
            check += delta
        times = np.array(times)
        
        if add_bounds:
            time_bounds = []
            delta = datetime.timedelta(minutes=30)
            for t in times.flat:
                time_bounds.append([t-delta,t+delta])
            time_bounds = np.array(time_bounds)
        else:
            time_bounds = None
        
        uid = np.arange(1,times.shape[0]+1)
        tdim = TemporalDimension(uid,times,bounds=time_bounds)

        return(tdim)
    
    def get_monthly_TemporalDimension(self,add_bounds=True):
        years = [2000,2001]
        months = range(1,13)
        times = np.empty(len(years)*len(months),dtype=object)
        time_bounds = np.empty((len(times),2),dtype=object)
        for idx,(year,month) in enumerate(itertools.product(years,months)):
            times[idx] = datetime.datetime(year,month,15)
            time_bounds[idx,0] = datetime.datetime(year,month,1)
            try:
                time_bounds[idx,1] = datetime.datetime(year,month+1,1)
            except ValueError:
                time_bounds[idx,1] = datetime.datetime(year+1,1,1)
        
        if not add_bounds:
            time_bounds = None
            
        uid = np.arange(1,times.shape[0]+1)
        tdim = TemporalDimension(uid,times,bounds=time_bounds)
        
        return(tdim)
    
    def test_TemporalGroupDimension(self):
        
        tdims = [
#                 self.get_hourly_TemporalDimension,
                 self.get_TemporalDimension,
                 self.get_monthly_TemporalDimension,
                 ]
        perms = ['year','month','day','hour','minute','second','microsecond']
#        perms = [['day','hour']]
        add_bounds_opts = [True,False]
#        add_bounds_opts = [True]
        for ii,add_bounds,tdim_func in itertools.product(range(1,4),add_bounds_opts,tdims):
            for perm in itertools.permutations(perms,ii):
                tdim = tdim_func(add_bounds=add_bounds)
                try:
                    tgdim = tdim.group(perm)
                except TypeError:
                    tgdim = tdim.group(*perm)
                for row in tgdim:
                    if np.random.rand() <= -0.01:
                        print (perm,add_bounds)
                        print row
                        import ipdb;ipdb.set_trace()
                    else:
                        continue
                self.assertEqual(np.sum([dgrp.sum() for dgrp in tgdim.dgroups]),len(tdim.value))

    def get_SpatialDimension(self):
        y = range(40,45)
        x = range(-90,-85)
        x,y = np.meshgrid(x,y)
        geoms = [Point(ix,iy) for ix,iy in zip(x.flat,y.flat)]
        geoms = np.array(geoms,dtype=object).reshape(5,5)
        np.random.seed(1)
        self._mask = np.array(np.random.random_integers(0,1,geoms.shape),dtype=bool)
        gid = np.arange(1,(self._mask.shape[0]*self._mask.shape[1])+1).reshape(self._mask.shape)
        gid = np.ma.array(gid,mask=self._mask)
        sdim = SpatialDimension(gid,geoms,self._mask)
        return(sdim)
    
    def test_SpatialDimension(self):
        sdim = self.get_SpatialDimension()
        masked = sdim.value.copy()
        self.assertTrue(np.all(masked.mask == self._mask))
        self.assertTrue(np.all(sdim.weights.mask == sdim.uid.mask))
        for row in sdim:
            pass

    def get_LevelDimension(self,add_bounds=True):
        values = np.array([50,150])
        if add_bounds:
            bounds = np.array([[0,100],[100,200]])
        else:
            bounds = None
        ldim = LevelDimension(np.arange(1,values.shape[0]+1),values,bounds)
        return(ldim)
    
    def test_LevelDimension(self):
        _add_bounds = [True,False]
        for add_bounds in _add_bounds:
            dim = self.get_LevelDimension(add_bounds)
            self.assertEqual(dim.shape,(2,))
            self.assertEqual(dim.storage.dtype.names,(dim._name_uid,dim._name_value))
    
    def get_OcgVariable(self,add_level=True,add_bounds=True,name='foo'):
        temporal = self.get_TemporalDimension(add_bounds)
        spatial = self.get_SpatialDimension()
        if add_level:
            level = self.get_LevelDimension(add_bounds)
            level_len = len(level.value)
        else:
            level = None
            level_len = 1
        
        value = np.random.rand(len(temporal.value),
                               level_len,
                               spatial.value.shape[0],
                               spatial.value.shape[1])
        mask = np.empty(value.shape,dtype=bool)
        for idx in range(mask.shape[0]):
            mask[idx,:,:] = spatial._value_mask
        value = np.ma.array(value,mask=mask)
        
        var = OcgVariable(name,value,temporal,spatial,level)
        return(var)
        
    def test_OcgCollection(self):
        _add_bounds = [
                       True,
                       False
                       ]
        _add_level = [True,False]
        _group = [None,['month'],['year'],['month','year']]
#        _group = [['month']]
        _iter_methods = [
                         'iter_rows',
                         'iter_list'
                         ]
        _aggregate = [
                      True,
                      False
                      ]
        args = (_add_bounds,_add_level,_group,_iter_methods,_aggregate)
        
        for add_bounds,add_level,group,iter_method,aggregate in itertools.product(*args):
#            print add_bounds,add_level
            coll = OcgCollection()
            var1 = self.get_OcgVariable(add_level=add_level,add_bounds=add_bounds)
            coll.add_variable(var1)
            var2 = self.get_OcgVariable(add_level=add_level,add_bounds=add_bounds,name='foo2')
            coll.add_variable(var2)
            self.assertEqual(len(coll.variables),2)
            
            if aggregate:
                for var in [var1,var2]:
                    prev_len = len(var.spatial)
                    var.aggregate()
                    self.assertEqual(len(var.spatial),1)
                    self.assertTrue(prev_len > len(var.spatial))
#                    import ipdb;ipdb.set_trace()
                    try:
                        self.assertAlmostEqual(var.value.mean(),var.raw_value.mean(),delta=1e-5)
                    except:
                        import ipdb;ipdb.set_trace()
            
            if group is not None:
                cnames = ['my_mean','my_median']
                for name in cnames:
                    for var in [var1,var2]:
                        var.group(group)
                        new_values = np.random.rand(var.temporal_group.shape[0],
                                                    var.value.shape[1],
                                                    var.spatial.value.shape[0],
                                                    var.spatial.value.shape[1])
                        mask = np.empty(new_values.shape,dtype=bool)
                        mask[:] = var.value.mask[0,0,:]
                        new_values = np.ma.array(new_values,mask=mask)
                        var.calc_value.update({name:new_values})
                        coll.add_calculation(var)
                for var in [var1,var2]: self.assertEqual(len(var.calc_value),2)
                self.assertTrue(np.all([c in coll.cid.storage[:,1] for c in cnames]))
            
            if add_level:
                m = 2
            else:
                m = 1
            it = MeltedIterator(coll)
            if group is None:
                iter_len = len(var1.temporal)*len(var1.spatial)*m*2
            else:
                iter_len = len(var1.temporal_group)*len(var1.spatial)*m*len(cnames)*2
            it_method = getattr(it,iter_method)
            headers = it.get_headers()
            for ii,row in enumerate(it_method(),start=1):
                if np.random.rand() <= -0.1:
                    import ipdb;ipdb.set_trace()
                if iter_method == 'iter_rows':
                    if add_level:
                        self.assertTrue(row['level'] is not None)
                    else:
                        self.assertTrue(row['level'] is None)
                    if group is None:
                        assert_keys = ['lid','ugid','vid','level','did','var_name','uri','value','gid','geom','time','tid']
                        self.assertEqual(len(set(row.keys()).difference(assert_keys)),0)
                        self.assertEqual(len(row),12)
                    else:
                        self.assertTrue(all([v in row.keys() for v in ['cid','calc_name']]))
                        self.assertEqual(len(row),13+len(group))
                else:
                    self.assertEqual(len(row[0]),len(headers))
                    self.assertTrue(type(row[1]) == Point)
                    if group is not None:
                        for g in group: self.assertTrue(g in headers)
            self.assertEqual(iter_len,ii)

    def test_OcgVariable_get_empty(self):
        empty = OcgVariable.get_empty('foo')
        self.assertTrue(empty.level is None)
        self.assertEqual(empty.spatial.shape,(0,))
        self.assertEqual(empty.temporal.shape,(0,))


if __name__ == "__main__":
#    import sys;sys.argv = ['', 'TestCollection.test_OcgVariable']
    unittest.main()