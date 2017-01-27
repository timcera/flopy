import os
import sys
import collections
import numpy as np
from flopy.pakbase import Package


# Create HeadObservation instance from a time series array

class HeadObservation(object):
    """
    Create HeadObservation instance from a time series array

    Parameters
    ----------
    tomulth : float
        time-offset multiplier for head observations. Default is 1.
    obsnam : string
        Observation name. Default is 'HOBS'
    layer : int
        is the zero-based layer index of the cell in which the head observation
        is located. If layer is less than zero, hydraulic heads from multiple
        layers are combined to calculate a simulated value. The number of
        layers equals the absolute value of layer, or |layer|. Default is 0.
    row : int
        zero-based row index for the observation. Default is 0.
    column : int
        zero-based column index of the observation. Default is 0.
    irefsp : int
        Stress period to which the observation time is referenced. The reference
        point is the beginning of the specified stress period. If the value of
        irefsp is negative, there are observations at |irefsp| times.
    roff : float
        Fractional offset from center of cell in Y direction (between rows).
        Default is 0.
    coff : float
        Fractional offset from center of cell in X direction (between columns).
        Default is 0.
    itt : int
        Flag that identifies whether head or head changes are used as
        observations. itt = 1 specified for heads and itt = 2 specified
        if initial value is head and subsequent changes in head. Only
        specified if irefsp is < 0. Default is 1.
    mlay : dictionary of length (|irefsp|)
        key represents zero-based layer numbers for multilayer observations an
        value represents the fractional value for each layer of multilayer
        observations. Only used if irefsp < 0. Default is {0:1.}
    time_series_data : list or numpy array
        two-dimensional list or numpy array containing the simulation time of
        the observation and the observed head [[totim, hob]]. Default is
        [[0., 0.]]

    Returns
    -------
    obs : HeadObservation
        HeadObservation object.

    Examples
    --------

    >>> import flopy
    >>> model = flopy.modflow.Modflow()
    >>> dis = flopy.modflow.ModflowDis(model, nlay=1, nrow=11, ncol=11, nper=2,
    ... perlen=[1,1])
    >>> obs = flopy.modflow.HeadObservation(model, layer=0, row=5, column=5,
    ... time_series_data=[[1.,54.4], [2., 55.2]])

    """

    def __init__(self, model, tomulth=1., obsname='HOBS',
                 layer=0, row=0, column=0, irefsp=0,
                 roff=0., coff=0., itt=1, mlay={0: 1.},
                 time_series_data=[[0., 0.]], names=None):

        self.obsname = obsname
        self.layer = layer
        self.row = row
        self.column = column
        self.irefsp = irefsp
        self.roff = roff
        self.coff = coff
        self.itt = itt

        # check if multilayer observation
        self.mlay = mlay
        self.maxm = 0
        self.multilayer = False
        if len(self.mlay.keys()) > 1:
            self.maxm = len(self.mlay.keys())
            self.multilayer = True
            tot = 0.
            for key, value in self.mlay.items():
                tot += value
            if tot != 1.:
                msg = 'sum of dataset 4 proportions must equal 1.0 - ' + \
                      'sum of dataset 4 proportions = {}'.format(tot)
                raise ValueError(msg)

        # convert passed time_series_data to a numpy array
        if isinstance(time_series_data, list):
            time_series_data = np.array(time_series_data, dtype=np.float)

        # if a single observation is passed as a list reshape to a
        # two-dimensional numpy array
        if len(time_series_data.shape) == 1:
            time_series_data = np.reshape(time_series_data, (1, 2))
        shape = time_series_data.shape

        # set the number of observations in this time series
        self.nobs = shape[0]

        # construct names if not passed
        if names is None:
            if self.nobs == 1:
                names = [obsname]
            else:
                names = []
                for idx in range(self.nobs):
                    names.append('{}.{}'.format(obsname, idx + 1))

        # create time_series_data
        self.time_series_data = HeadObservation.get_empty(ncells=shape[0])
        for idx in range(self.nobs):
            t = time_series_data[idx, 0]
            kstp, kper, toffset = model.dis.get_kstp_kper_toffset(t)
            self.time_series_data[idx]['totim'] = t
            self.time_series_data[idx]['irefsp'] = kper
            self.time_series_data[idx]['toffset'] = toffset / tomulth
            self.time_series_data[idx]['hobs'] = time_series_data[idx, 1]
            self.time_series_data[idx]['obsname'] = names[idx]

    @staticmethod
    def get_empty(ncells=0):
        # get an empty recaray that correponds to dtype
        dtype = HeadObservation.get_default_dtype()
        d = np.zeros((ncells, len(dtype)), dtype=dtype)
        d[:, :] = -1.0E+10
        d[:]['obsname'] = ''
        return np.core.records.fromarrays(d.transpose(), dtype=dtype)

    @staticmethod
    def get_default_dtype():
        # get the default HOB dtype
        dtype = np.dtype([("totim", np.float32), ("irefsp", np.int),
                          ("toffset", np.float32),
                          ("hobs", np.float32), ("obsname", '|S12')])
        return dtype


class ModflowHob(Package):
    """
    Head Observation package class

    Parameters
    ----------
    iuhobsv : int
        unit number where output is saved
    hobdry : float
        Value of the simulated equivalent written to the observation output file
        when the observation is omitted because a cell is dry
    tomulth : float
        Time step multiplier for head observations. The product of tomulth and
        toffset must produce a time value in units consistent with other model
        input. tomulth can be dimensionless or can be used to convert the units
        of toffset to the time unit used in the simulation.
    obs_data : list of HeadObservation instances
        list of HeadObservation instances containing all of the data for
        each observation. Default is None.
    hobname : str
        Name of head observation output file. If iuhobsv is greater than 0,
        and hobname is not provided the model basename with a '.hob.out'
        extension will be used. Default is None.
    extension : string
        Filename extension (default is ['hob'])
    unitnumber : int
        File unit number (default is [39])


    Attributes
    ----------

    Methods
    -------

    See Also
    --------

    Notes

    Examples
    --------

    >>> import flopy
    >>> model = flopy.modflow.Modflow()
    >>> dis = flopy.modflow.ModflowDis(model, nlay=1, nrow=11, ncol=11, nper=2,
    ... perlen=[1,1])
    >>> obs = flopy.modflow.HeadObservation(model, layer=0, row=5, column=5,
    ... time_series_data=[[1.,54.4], [2., 55.2]])
    >>> hob = flopy.modflow.ModflowHob(model, iuhobsv=51, hobdry=-9999.,
    ... obs_data=[obs])


    """

    def __init__(self, model, iuhobsv=None, hobdry=0, tomulth=1.0,
                 obs_data=None, hobname=None,
                 extension=['hob'], unitnumber=None):
        """
        Package constructor
        """
        # set default unit number of one is not specified
        if unitnumber is None:
            unitnumber = ModflowHob.defaultunit()

        if iuhobsv is not None:
            if iuhobsv > 0:
                if hobname is None:
                    hobname = model.name + '.hob.out'
                model.add_output(hobname, iuhobsv, output=True)
            else:
                iuhobsv = 0

        # Fill namefile items
        name = [ModflowHob.ftype()]
        units = [unitnumber]
        extra = ['']

        # Call ancestor's init to set self.parent, extension, name and unit
        # number
        Package.__init__(self, model, extension=extension, name=name,
                         unit_number=units, extra=extra)

        self.url = 'hob.htm'
        self.heading = '# {} package for '.format(self.name[0]) + \
                       ' {}, '.format(model.version_types[model.version]) + \
                       'generated by Flopy.'

        self.iuhobsv = iuhobsv
        self.hobdry = hobdry
        self.tomulth = tomulth

        # make sure obs_data is a list
        if not isinstance(obs_data, list):
            obs_data = [obs_data]

        # set self.obs_data
        self.obs_data = obs_data

        # add checks for input compliance (obsnam length, etc.)
        self.parent.add_package(self)

    def _set_dimensions(self):
        # make sure each entry of obs_data list is a HeadObservation instance
        # and calculate nh, mobs, and maxm
        msg = ''
        self.nh = 0
        self.mobs = 0
        self.maxm = 0
        for idx, obs in enumerate(self.obs_data):
            if not isinstance(obs, HeadObservation):
                msg += 'ModflowHob: obs_data entry {} '.format(idx) + \
                       'is not a HeadObservation instance.\n'
                continue
            self.nh += obs.nobs
            if obs.multilayer:
                self.mobs += obs.nobs
            self.maxm = max(self.maxm, obs.maxm)
        if msg != '':
            raise ValueError(msg)
        return

    def write_file(self):
        """
        Write the package file

        Returns
        -------
        None

        """
        # determine the dimensions of HOB data
        self._set_dimensions()

        # open file for writing
        f = open(self.fn_path, 'w')

        # write dataset 0
        f.write('{}\n'.format(self.heading))

        # write dataset 1
        f.write('{:10d}'.format(self.nh))
        f.write('{:10d}'.format(self.mobs))
        f.write('{:10d}'.format(self.maxm))
        f.write('{:10d}'.format(self.iuhobsv))
        f.write('{:10.4g}\n'.format(self.hobdry))

        # write dataset 2
        f.write('{:10.4g}\n'.format(self.tomulth))

        # write datasets 3-6
        for idx, obs in enumerate(self.obs_data):
            # dataset 3
            obsname = obs.obsname
            if isinstance(obsname, bytes):
                obsname = obsname.decode('utf-8')
            line = '{:12s}   '.format(obsname)
            layer = obs.layer
            if layer >= 0:
                layer += 1
            line += '{:10d}'.format(layer)
            line += '{:10d}'.format(obs.row + 1)
            line += '{:10d}'.format(obs.column + 1)
            irefsp = obs.irefsp
            if irefsp >= 0:
                irefsp += 1
            line += '{:10d}'.format(irefsp)
            if obs.nobs == 1:
                toffset = obs.obs_data[0]['toffset']
                hobs = obs.obs_data[0]['hobs']
            else:
                toffset = 0.
                hobs = 0.
            line += '{:10.2f}'.format(toffset)
            line += '{:10.4f}'.format(obs.roff)
            line += '{:10.4f}'.format(obs.coff)
            line += '{:10.4f}'.format(hobs)
            line += '  # DATASET 3 - Observation {}'.format(idx + 1)
            f.write('{}\n'.format(line))

            # dataset 4
            if len(obs.mlay.keys()) > 1:
                line = ''
                for key, value in obs.items():
                    line += '{:5d}{:10.4f}'.format(key + 1, value)
                line += '  # DATASET 4 - Observation {}'.format(idx + 1)
                f.write('{}\n'.format(line))

            # dataset 5
            if irefsp < 0:
                line = '{:10d}'.format(obs.itt)
                line += 85 * ' '
                line += '  # DATASET 5 - Observation {}'.format(idx + 1)
                f.write('{}\n'.format(line))

            # dataset 6:
            if obs.nobs > 1:
                for jdx, t in enumerate(obs.time_series_data):
                    obsname = t['obsname']
                    if isinstance(obsname, bytes):
                        obsname = obsname.decode('utf-8')
                    line = '{:12s}   '.format(obsname)
                    line += '{:10d}'.format(t['irefsp'] + 1)
                    line += '{:10.4f}'.format(t['toffset'])
                    line += '{:10.4f}'.format(t['hobs'])
                    line += 50 * ' '
                    line += '  # DATASET 6 - ' + \
                            'Observation {}.{}'.format(idx + 1, jdx + 1)
                    f.write('{}\n'.format(line))

        # close the hob package file
        f.close()

        return

    @staticmethod
    def load(f, model, ext_unit_dict=None, check=True):
        """
        Load an existing package.

        Parameters
        ----------
        f : filename or file handle
            File to load.
        model : model object
            The model object (of type :class:`flopy.modflow.mf.Modflow`) to
            which this package will be added.
        ext_unit_dict : dictionary, optional
            If the arrays in the file are specified using EXTERNAL,
            or older style array control records, then `f` should be a file
            handle.  In this case ext_unit_dict is required, which can be
            constructed using the function
            :class:`flopy.utils.mfreadnam.parsenamefile`.
        check : boolean
            Check package data for common errors. (default True)

        Returns
        -------
        hob : ModflowHob object
            ModflowHob object.

        Examples
        --------

        >>> import flopy
        >>> m = flopy.modflow.Modflow()
        >>> hobs = flopy.modflow.ModflowHob.load('test.hob', m)

        """

        if model.verbose:
            sys.stdout.write('loading hob package file...\n')

        if not hasattr(f, 'read'):
            filename = f
            f = open(filename, 'r')
        # dataset 0 -- header
        while True:
            line = f.readline()
            if line[0] != '#':
                break

        # read dataset 1
        t = line.strip().split()
        nh = int(t[0])
        # mobs = int(t[1])
        # maxm = int(t[2])
        iuhobsv = int(t[3])
        #if iuhobsv > 0:
        #    model.add_pop_key_list(iuhobsv)
        hobdry = float(t[4])

        # read dataset 2
        line = f.readline()
        t = line.strip().split()
        tomulth = float(t[0])

        # read observation data
        obs_data = []

        # read datasets 3-6
        nobs = 0
        while True:
            # read dataset 3
            line = f.readline()
            t = line.strip().split()
            obsnam = t[0]
            layer = int(t[1])
            row = int(t[2]) - 1
            col = int(t[3]) - 1
            irefsp0 = int(t[4])
            toffset = float(t[5])
            roff = float(t[6])
            coff = float(t[7])
            hob = float(t[8])

            # read dataset 4 if multilayer obs
            if layer > 0:
                layer -= 1
                mlay = {layer: 1.}
            else:
                line = f.readline()
                t = line.strip().split()
                mlay = collections.OrderedDict()
                for j in range(0, abs(layer), 2):
                    k = int(t[j]) - 1
                    mlay[k] = float(t[j + 1])

            # read datasets 5 & 6. Index loop variable
            if irefsp0 > 0:
                itt = 1
                irefsp -= 1
                totim = model.dis.get_totim_from_kper_toffset(irefsp0,
                                                              toffset * tomulth)
                names = [obsnam]
                tsd = [totim, hob]
                nobs += 1
            else:
                names = []
                tsd = []
                # read data set 5
                line = f.readline()
                t = line.strip().split()
                itt = int(t[0])
                # dataset 6
                for j in range(abs(irefsp0)):
                    line = f.readline()
                    t = line.strip().split()
                    names.append(t[0])
                    irefsp = int(t[1]) - 1
                    toffset = float(t[2])
                    totim = model.dis.get_totim_from_kper_toffset(irefsp,
                                                                  toffset * tomulth)
                    hob = float(t[3])
                    tsd.append([totim, hob])
                    nobs += 1

            obs_data.append(HeadObservation(model, tomulth=tomulth,
                                            layer=layer, row=row, column=col,
                                            irefsp=irefsp0,
                                            roff=roff, coff=coff,
                                            obsname=obsnam,
                                            mlay=mlay, itt=itt,
                                            time_series_data=tsd,
                                            names=names))
            if nobs == nh:
                break

        # close the file
        f.close()

        # determine specified unit number
        unitnumber = None
        hobname = None
        if ext_unit_dict is not None:
            for key, value in ext_unit_dict.items():
                if value.filetype == ModflowHob.ftype():
                    unitnumber = key
                if key == iuhobsv:
                    hobname = os.path.basename(value.filename)
                    model.add_pop_key_list(iuhobsv)


        # create hob object instance
        hob = ModflowHob(model, iuhobsv=iuhobsv, hobdry=hobdry,
                         tomulth=tomulth, obs_data=obs_data,
                         unitnumber=unitnumber, hobname=hobname)

        return hob

    @staticmethod
    def ftype():
        return 'HOB'

    @staticmethod
    def defaultunit():
        return 39