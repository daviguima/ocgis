import numpy as np
import itertools
from shapely.geometry.polygon import Polygon
from collections import namedtuple
import os
import tempfile
import warnings
from osgeo import ogr, osr
from shapely import wkt, wkb
from numpy.ma.core import MaskedArray
from ocgis import env


def vprint(msg):
    if env.VERBOSE:
        print(msg)


def iter_array(a,use_mask=True,return_value=False):
    try:
        iter_args = [range(0,ii) for ii in a.shape]
    except AttributeError:
        a = np.array(a)
        iter_args = [range(0,ii) for ii in a.shape]
    if use_mask and not isinstance(a,MaskedArray):
        use_mask = False
    for ii in itertools.product(*iter_args):
        if use_mask:
            if not a.mask[ii]:
                idx = ii
            else:
                continue
        else:
            idx = ii
        if return_value:
            ret = (idx,a[ii])
        else:
            ret = idx
        yield(ret)

def geom_to_mask(coll):
    coll['geom'] = np.ma.array(coll['geom'],mask=coll['geom_mask'])
    return(coll)

def mask_to_geom(coll):
    coll['geom'] = np.array(coll['geom'])
    return(coll)
    
def itersubclasses(cls, _seen=None):
    """
    itersubclasses(cls)

    Generator over all subclasses of a given class, in depth first order.

    >>> list(itersubclasses(int)) == [bool]
    True
    >>> class A(object): pass
    >>> class B(A): pass
    >>> class C(A): pass
    >>> class D(B,C): pass
    >>> class E(D): pass
    >>> 
    >>> for cls in itersubclasses(A):
    ...     print(cls.__name__)
    B
    D
    E
    C
    >>> # get ALL (new-style) classes currently defined
    >>> [cls.__name__ for cls in itersubclasses(object)] #doctest: +ELLIPSIS
    ['type', ...'tuple', ...]
    """
    
    if not isinstance(cls, type):
        raise TypeError('itersubclasses must be called with '
                        'new-style classes, not %.100r' % cls)
    if _seen is None: _seen = set()
    try:
        subs = cls.__subclasses__()
    except TypeError: # fails only when cls is type
        subs = cls.__subclasses__(cls)
    for sub in subs:
        if sub not in _seen:
            _seen.add(sub)
            yield sub
            for sub in itersubclasses(sub, _seen):
                yield sub
                
def approx_resolution(vec):
    """
    >>> vec = [1,2,3,4,5]
    >>> approx_resolution(vec)
    1.0
    """
    diff = []
    for i in range(len(vec)):
        curr = vec[i]
        try:
            nxt = vec[i+1]
            diff.append(abs(curr-nxt))
        except IndexError:
            break
    return(np.mean(diff))

def keep(prep_igeom=None,igeom=None,target=None):
    test_geom = prep_igeom or igeom
    if test_geom.intersects(target) and not target.touches(igeom):
        ret = True
    else:
        ret = False
    return(ret)

def prep_keep(prep_igeom,igeom,target):
    if prep_igeom.intersects(target) and not target.touches(igeom):
        ret = True
    else:
        ret = False
    return(ret)

def contains(grid,lower,upper,res=0.0):
    
    ## small ranges on coordinates requires snapping to closest coordinate
    ## to ensure values are selected through logical comparison.
    ugrid = np.unique(grid)
    lower = ugrid[np.argmin(np.abs(ugrid-(lower-0.5*res)))]
    upper = ugrid[np.argmin(np.abs(ugrid-(upper+0.5*res)))]
    
    s1 = grid >= lower
    s2 = grid <= upper
    ret = s1*s2

    return(ret)

#def itr_array(a):
#    "a -- 2-d ndarray"
#    assert(len(a.shape) == 2)
#    ix = a.shape[0]
#    jx = a.shape[1]
#    for ii,jj in itertools.product(range(ix),range(jx)):
#        yield ii,jj
        
def make_poly(rtup,ctup):
    """
    rtup = (row min, row max)
    ctup = (col min, col max)
    """
    return Polygon(((ctup[0],rtup[0]),
                    (ctup[0],rtup[1]),
                    (ctup[1],rtup[1]),
                    (ctup[1],rtup[0])))
    
def sub_range(a):
    """
    >>> vec = np.array([2,5,9])
    >>> sub_range(vec)
    array([2, 3, 4, 5, 6, 7, 8, 9])
    """
    a = np.array(a)
#    ## for the special case of the array with one element
#    if len(a) == 1:
#        ret = np.arange(a[0],a[0]+1)
#    else:
    ret = np.arange(a.min(),a.max()+1)
    return(ret)

def bounding_coords(polygon):
    min_x,min_y,max_x,max_y = polygon.bounds
    Bounds = namedtuple('Bounds',['min_x','min_y','max_x','max_y'])
    return(Bounds(min_x=min_x,
                  max_x=max_x,
                  min_y=min_y,
                  max_y=max_y))
    
def shapely_to_shp(obj,outname):
    from osgeo import osr, ogr
    
    path = os.path.join('/tmp',outname+'.shp')
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    ogr_geom = 3
    
    dr = ogr.GetDriverByName('ESRI Shapefile')
    ds = dr.CreateDataSource(path)
    try:
        if ds is None:
            raise IOError('Could not create file on disk. Does it already exist?')
            
        layer = ds.CreateLayer('lyr',srs=srs,geom_type=ogr_geom)
        feature_def = layer.GetLayerDefn()
        feat = ogr.Feature(feature_def)
        try:
            iterator = iter(obj)
        except TypeError:
            iterator = iter([obj])
        for geom in iterator:
            feat.SetGeometry(ogr.CreateGeometryFromWkb(geom.wkb))
            layer.CreateFeature(feat)
    finally:
        ds.Destroy()
        


def get_temp_path(suffix='',name=None,nest=False,only_dir=False,wd=None):
    """Return absolute path to a temporary file."""

    def _get_wd_():
        if wd is None:
            return(tempfile.gettempdir())
        else:
            return(wd)

    if nest:
        f = tempfile.NamedTemporaryFile()
        f.close()
        dir = os.path.join(_get_wd_(),os.path.split(f.name)[-1])
        os.mkdir(dir)
    else:
        dir = _get_wd_()
    if only_dir:
        ret = dir
    else:
        if name is not None:
            ret = os.path.join(dir,name+suffix)
        else:
            f = tempfile.NamedTemporaryFile(suffix=suffix,dir=dir)
            f.close()
            ret = f.name
    return(str(ret))

def get_wkt_from_shp(path,objectid,layer_idx=0):
    """
    >>> path = '/home/bkoziol/git/OpenClimateGIS/bin/shp/state_boundaries.shp'
    >>> objectid = 10
    >>> wkt = get_wkt_from_shp(path,objectid)
    >>> assert(wkt.startswith('POLYGON ((-91.730366281818348 43.499571367976877,'))
    """
    ds = ogr.Open(path)
    try:
        lyr = ds.GetLayerByIndex(layer_idx)
        lyr_name = lyr.GetName()
        if objectid is None:
            sql = 'SELECT * FROM {0}'.format(lyr_name)
        else:
            sql = 'SELECT * FROM {0} WHERE ObjectID = {1}'.format(lyr_name,objectid)
        data = ds.ExecuteSQL(sql)
        #import pdb; pdb.set_trace()
        feat = data.GetNextFeature()
        geom = feat.GetGeometryRef()
        wkt = geom.ExportToWkt()
        return(wkt)
    finally:
        ds.Destroy()

   
class ShpIterator(object):
    
    def __init__(self,path):
        assert(os.path.exists(path))
        self.path = path
        
    def iter_features(self,fields,lyridx=0,geom='geom',skiperrors=False,
                      to_shapely=False):
        
        ##tdk
#        to_sr = osr.SpatialReference()
#        to_sr.ImportFromProj4('+proj=longlat +datum=WGS84 +pm=180dW +over ')
#        to_sr.ImportFromProj4('+proj=longlat +datum=WGS84 +lon_wrap=180 ')
        ##tdk
        
        ds = ogr.Open(self.path)
        try:
            lyr = ds.GetLayerByIndex(lyridx)
            lyr.ResetReading()
            for feat in lyr:
                ## get the values
                values = []
                for field in fields:
                    try:
                        values.append(feat.GetField(field))
                    except:
                        try:
                            if skiperrors is True:
                                warnings.warn('Error in GetField("{0}")'.format(field))
                            else:
                                raise
                        except ValueError:
                            msg = 'Illegal field requested in GetField("{0}")'.format(field)
                            raise ValueError(msg)
#                values = [feat.GetField(field) for field in fields]
                attrs = dict(zip(fields,values))
                ## get the geometry
                
                ##tdk
                wkt_str = feat.GetGeometryRef().ExportToWkt()
#                geom_obj = feat.GetGeometryRef()
#                geom_obj.TransformTo(to_sr)
#                wkt_str = geom_obj.ExportToWkt()
                ##tdk
                
                if to_shapely:
                    ## additional load to clean geometries
                    geom_data = wkt.loads(wkt_str)
                    geom_data = wkb.loads(geom_data.wkb)
                else:
                    geom_data = wkt_str
                attrs.update({geom:geom_data})
                yield attrs
        finally:
            ds.Destroy()


def get_shp_as_multi(path,uid_field=None,attr_fields=[],make_id=False,id_name='ugid'):
    """
    >>> path = '/home/bkoziol/git/OpenClimateGIS/bin/shp/state_boundaries.shp'
    >>> uid_field = 'objectid'
    >>> ret = get_shp_as_multi(path,uid_field)
    """
    if uid_field is None or uid_field == '':
        uid_field = []
    else:
        uid_field = [str(uid_field)]
    fields = uid_field + attr_fields
    shpitr = ShpIterator(path)
    data = [feat for feat in shpitr.iter_features(fields,to_shapely=True)]
    ## add unique identifier if requested and the passed uid field is none
    for ii,gd in enumerate(data,start=1):
        if len(uid_field) == 0 and make_id is True:
            gd[id_name] = ii
        else:
            geom_id = gd.pop(uid_field[0])
            gd[id_name] = int(geom_id)
    
#    ## check the WKT is a polygon and the unique identifier is a unique integer
#    uids = []
#    for feat in data:
#        if len(uid_field) > 0:
#            feat[uid_field[0]] = int(feat[uid_field[0]])
#            uids.append(feat[uid_field[0]])
#    assert(len(uids) == len(set(uids)))
    return(data)

def get_sr(srid):
    sr = osr.SpatialReference()
    sr.ImportFromEPSG(srid)
    return(sr)

def get_area(geom,sr_orig,sr_dest):
    geom = ogr.CreateGeometryFromWkb(geom.wkb)
    geom.AssignSpatialReference(sr_orig)
    geom.TransformTo(sr_dest)
    return(geom.GetArea())

def get_area_srid(geom,srid_orig,srid_dest):
    sr = get_sr(srid_orig)
    sr2 = get_sr(srid_dest)
    return(get_area(geom,sr,sr2))