from util.ncconv.experimental.ocg_dataset import OcgDataset
import ipdb


## this is the function to map
def f(arg):
    from util.ncconv.experimental.ocg_dataset import OcgDataset
    import multiprocessing as mp
    
    ## see http://mail.python.org/pipermail/python-list/2011-March/1268178.html
    ## tdk: will have to evaluate if any problems arise with this code.
    mp.current_process().daemon = False
    
    uri = arg[0]
    ocg_opts = arg[1]
    var_name = arg[2]
    polygon = arg[3]
    time_range = arg[4]
    level_range = arg[5]
    clip = arg[6]
    union = arg[7]
    subpoly_proc = arg[8]
    
    ocg_dataset = OcgDataset(uri,**ocg_opts)
    if subpoly_proc <= 1:
        sub = ocg_dataset.subset(var_name,polygon,time_range,level_range)
        if clip: sub.clip(polygon)
        if union: sub.union()
    else:
        subset_opts = dict(time_range=time_range,
                           polygon=polygon)
        subs = ocg_dataset.mapped_subset(var_name,
                                         max_proc=subpoly_proc,
                                         subset_opts=subset_opts)
        subs = ocg_dataset.parallel_process_subsets(subs,
                                                    clip=clip,
                                                    union=union,
                                                    polygon=polygon)
        sub = ocg_dataset.combine_subsets(subs,union=union)
    return(sub)


def multipolygon_operation(uri,
                           var_name,
                           ocg_opts = {},
                           polygons=None,
                           time_range=None,
                           level_range=None,
                           clip=False,
                           union=False,
                           in_parallel=False,
                           max_proc=4,
                           max_proc_per_poly=4):
    
    ## make the sure the polygon object is iterable
    if polygons is None:
        if clip:
            raise(ValueError('If clip is requested, polygon boundaries must be passed.'))
        polygons = [None]
    else:
        ## ensure polygon list is iterable
        if type(polygons) not in [list,tuple]:
            polygons = [polygons]
    
    ## switch depending on parallel request
    if in_parallel:
        import multiprocessing as mp
        
        ## construct the pool. first, calculate number of remaining processes
        ## to allocate to sub-polygon processing.
        if len(polygons) <= max_proc:
            poly_proc = len(polygons)
            subpoly_proc = max_proc - len(polygons)
        else:
            poly_proc = max_proc
            subpoly_proc = 0
        ## distribute the remaining processes to the polygons
        subpoly_proc = subpoly_proc / len(polygons)
        ## ensure we don't exceed the maximum processes per polygon
        if subpoly_proc > max_proc_per_poly:
            subpoly_proc = max_proc_per_poly
        ## assemble the argument list
        args = []
        for polygon in polygons:
            arg = [uri,ocg_opts,var_name,polygon,time_range,level_range,clip,union,subpoly_proc]
            args.append(arg)
        pool = mp.Pool(poly_proc)
        subs = pool.map(f,args)
    else:
        subs = []
        ## loop through each polygon
        for polygon in polygons:
            ocg_dataset = OcgDataset(uri,**ocg_opts)
            sub = ocg_dataset.subset(var_name,polygon,time_range,level_range)
            if clip: sub.clip(polygon)
            if union: sub.union()
            subs.append(sub)
    ## merge subsets
    for ii,sub in enumerate(subs):
        ## keep the first one separate to merge against
        if ii == 0:
            base = sub
        else:
            base = base.merge(sub)
    
    return(base)