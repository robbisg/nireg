from tempfile import NamedTemporaryFile

import numpy as np
from neuroimaging.testing import *


from neuroimaging.utils.tests.data import repository

from neuroimaging.core.image import image

from neuroimaging.core.api import Image, load_image, save_image, fromarray
from neuroimaging.core.api import parcels, data_generator, write_data

from neuroimaging.core.reference.coordinate_map import CoordinateMap
from neuroimaging.core.reference.mapping import Affine

class TestImage(TestCase):

    def setUp(self):
        self.img = load_image(str(repository._fullpath('avg152T1.nii.gz')))
        self.tmpfile = NamedTemporaryFile(suffix='.nii.gz')
        
    def test_init(self):
        new = Image(np.asarray(self.img), self.img.coordmap)
        assert_equal(np.asarray(self.img)[:], np.asarray(new)[:])

        self.assertRaises(ValueError, Image, None, None)

    def test_badfile(self):
        filename = "bad_file.foo"
        self.assertRaises(RuntimeError, load_image, filename)

    def test_maxmin_values(self):
        y = np.asarray(self.img)
        self.assertEquals(y.shape, tuple(self.img.coordmap.shape))
        np.allclose(y.max(), 437336.36, rtol=1.0e-8)
        self.assertEquals(y.min(), 0.0)

    def test_slice_plane(self):
        x = self.img[3]
        self.assertEquals(x.shape, self.img.shape[1:])
        self.assertEquals(x.shape, x.coordmap.shape)

    def test_slice_block(self):
        x = self.img[3:5]
        self.assertEquals(x.shape, (2,) + tuple(self.img.coordmap.shape[1:]))
        self.assertEquals(x.shape, x.coordmap.shape)

    def test_slice_step(self):
        s = slice(0,20,2)
        x = self.img[s]
        self.assertEquals(x.shape, (10,) + tuple(self.img.coordmap.shape[1:]))
        self.assertEquals(x.shape, x.coordmap.shape)

    def test_slice_type(self):
        s = slice(0,self.img.coordmap.shape[0])
        x = self.img[s]
        self.assertEquals(x.shape, tuple((self.img.coordmap.shape)))
        self.assertEquals(x.shape, x.coordmap.shape)

    def test_slice_steps(self):
        zdim, ydim, xdim = self.img.shape
        slice_z = slice(0, zdim, 2)
        slice_y = slice(0, ydim, 2)
        slice_x = slice(0, xdim, 2)
        x = self.img[slice_z, slice_y, slice_x]
        newshape = ((zdim/2)+1, (ydim/2)+1, (xdim/2)+1)
        self.assertEquals(x.shape, newshape)

    def test_array(self):
        x = np.asarray(self.img)
        assert isinstance(x, np.ndarray)
        self.assertEquals(x.shape, self.img.shape)
        self.assertEquals(x.ndim, self.img.ndim)
        
    # FIXME: AssertionError: Arrays are not equal.
    # This is a bug in the pyniftiio.py file where a one-voxel offset
    # is added to the affine.  This does not conform with the nifti1.h
    # standard and will be removed asap.
    @dec.knownfailure
    def test_file_roundtrip(self):
        save_image(self.img, self.tmpfile.name)
        img2 = load_image(self.tmpfile.name)
        data = np.asarray(self.img)
        data2 = np.asarray(img2)
        # verify data
        assert_almost_equal(data2, data)
        assert_almost_equal(data2.mean(), data.mean())
        assert_almost_equal(data2.min(), data.min())
        assert_almost_equal(data2.max(), data.max())
        # verify shape and ndims
        assert_equal(img2.shape, self.img.shape)
        assert_equal(img2.ndim, self.img.ndim)
        # verify affine
        assert_equal(img2.affine, self.img.affine)

    # This is a bug in the pyniftiio.py file where a one-voxel offset
    # is added to the affine.  This does not conform with the nifti1.h
    # standard and will be removed asap.
    @dec.knownfailure
    def test_roundtrip_fromarray(self):
        data = np.random.rand(10,20,30)
        img = fromarray(data)
        save_image(img, self.tmpfile.name)
        img2 = load_image(self.tmpfile.name)
        data2 = np.asarray(img2)
        # verify data
        assert_almost_equal(data2, data)
        assert_almost_equal(data2.mean(), data.mean())
        assert_almost_equal(data2.min(), data.min())
        assert_almost_equal(data2.max(), data.max())
        # verify shape and ndims
        assert_equal(img2.shape, img.shape)
        assert_equal(img2.ndim, img.ndim)
        # verify affine
        assert_equal(img2.affine, img.affine)

    # FIXME: AssertionError: Arrays are not almost equal
    # This is a bug in the pyniftiio.py file where a one-voxel offset
    # is added to the affine.  This does not conform with the nifti1.h
    # standard and will be removed asap.
    @dec.knownfailure
    def test_nondiag(self):
        self.img.coordmap.mapping.transform[0,1] = 3.0
        save_image(self.img, self.tmpfile.name)
        img2 = load_image(self.tmpfile.name)
        assert_almost_equal(img2.coordmap.mapping.transform,
                                       self.img.coordmap.mapping.transform)

    def test_generator(self):
        gen = data_generator(self.img)
        for ind, data in gen:
            self.assertEquals(data.shape, (109,91))

    def test_iter(self):
        imgiter = iter(self.img)
        for data in imgiter:
            self.assertEquals(data.shape, (109,91))

    def test_iter4(self):
        tmp = Image(np.zeros(self.img.shape), self.img.coordmap)
        write_data(tmp, data_generator(self.img, range(self.img.shape[0])))
        assert_almost_equal(np.asarray(tmp), np.asarray(self.img))

    def test_iter5(self):
        #This next test seems like it could be deprecated with
        #simplified iterator options
        
        tmp = Image(np.zeros(self.img.shape), self.img.coordmap)
        g = data_generator(self.img)
        write_data(tmp, g)
        assert_almost_equal(np.asarray(tmp), np.asarray(self.img))

    def test_parcels1(self):
        rho = self.img
        parcelmap = (np.asarray(rho)[:] * 100).astype(np.int32)
        
        test = np.zeros(parcelmap.shape)
        v = 0
        for i, d in data_generator(test, parcels(parcelmap)):
            v += d.shape[0]

        self.assertEquals(v, np.product(test.shape))

    def test_parcels3(self):
        rho = self.img[0]
        parcelmap = (np.asarray(rho)[:] * 100).astype(np.int32)
        labels = np.unique(parcelmap)
        test = np.zeros(rho.shape)

        v = 0
        for i, d in data_generator(test, parcels(parcelmap, labels=labels)):
            v += d.shape[0]

        self.assertEquals(v, np.product(test.shape))

    def uint8_to_dtype(self, dtype):
        dtype = dtype
        shape = (2,3,4)
        dmax = np.iinfo(np.uint8).max
        data = np.random.randint(0, dmax, size=shape)
        data[0,0,0] = 0
        data[1,0,0] = dmax
        data = data.astype(np.uint8) # randint returns np.int32
        img = fromarray(data)
        newimg = save_image(img, self.tmpfile.name, dtype=dtype)
        newdata = np.asarray(newimg)
        return newdata, data
        
    def test_scaling_uint8_to_uint8(self):
        dtype = np.uint8
        newdata, data = self.uint8_to_dtype(dtype)
        assert_equal(newdata, data)

    def test_scaling_uint8_to_uint16(self):
        dtype = np.uint16
        newdata, data = self.uint8_to_dtype(dtype)
        assert_equal(newdata, data)

    def test_scaling_uint8_to_float32(self):
        dtype = np.float32
        newdata, data = self.uint8_to_dtype(dtype)
        assert_equal(newdata, data)

    def test_scaling_uint8_to_int32(self):
        dtype = np.int32
        newdata, data = self.uint8_to_dtype(dtype)
        assert_equal(newdata, data)
    
    def float32_to_dtype(self, dtype):
        # Utility function for the float32_to_<dtype> functions
        # below. There is a lot of shared functionality, split up so
        # the function names are unique so it's clear which dtypes are
        # involved in a failure.
        dtype = dtype
        shape = (2,3,4)
        # set some value value for scaling our data
        scale = np.iinfo(np.uint16).max * 2.0
        data = np.random.normal(size=(2,3,4), scale=scale)
        data[0,0,0] = np.finfo(np.float32).max
        data[1,0,0] = np.finfo(np.float32).min
        # random.normal will return data as native machine type
        data = data.astype(np.float32)
        img = fromarray(data)
        newimg = save_image(img, self.tmpfile.name, dtype=dtype)
        newdata = np.asarray(newimg)
        return newdata, data
        
    def test_scaling_float32_to_uint8(self):
        dtype = np.uint8
        newdata, data = self.float32_to_dtype(dtype)
        assert_equal(newdata, data)

    def test_scaling_float32_to_uint16(self):
        dtype = np.uint16
        newdata, data = self.float32_to_dtype(dtype)
        assert_equal(newdata, data)
        
    def test_scaling_float32_to_int16(self):
        dtype = np.int16
        newdata, data = self.float32_to_dtype(dtype)
        assert_equal(newdata, data)

    def test_scaling_float32_to_float32(self):
        dtype = np.float32
        newdata, data = self.float32_to_dtype(dtype)
        assert_equal(newdata, data)

    def test_header_roundtrip(self):
        hdr = self.img.header
        # Update some header values and make sure they're saved
        hdr['slice_duration'] = 0.200
        hdr['intent_p1'] = 2.0
        hdr['descrip'] = 'descrip for TestImage:test_header_roundtrip'
        hdr['slice_end'] = 12
        self.img.header = hdr
        save_image(self.img, self.tmpfile.name)
        newimg = load_image(self.tmpfile.name)
        newhdr = newimg.header
        assert_almost_equal(newhdr['slice_duration'], hdr['slice_duration'])
        assert_equal(newhdr['intent_p1'], hdr['intent_p1'])
        assert_equal(newhdr['descrip'], hdr['descrip'])
        assert_equal(newhdr['slice_end'], hdr['slice_end'])
        
def test_slicing_returns_image():
    data = np.ones((2,3,4))
    img = fromarray(data)
    assert isinstance(img, Image)
    assert img.ndim == 3
    # 2D slice
    img2D = img[:,:,0]
    assert isinstance(img2D, Image)
    assert img2D.ndim == 2
    # 1D slice
    img1D = img[:,0,0]
    assert isinstance(img1D, Image)
    assert img1D.ndim == 1


class ArrayLikeObj(object):
    """The data attr in Image is an array-like object.
    Test the array-like interface that we'll expect to support."""
    def __init__(self):
        self._data = np.ones((2,3,4))
    
    def get_ndim(self):
        return self._data.ndim
    ndim = property(get_ndim)
        
    def get_shape(self):
        return self._data.shape
    shape = property(get_shape)

    def __getitem__(self, index):
        return self._data[index]

    def __setitem__(self, index, value):
        self._data[index] = value

    def __array__(self):
        return self._data

def test_ArrayLikeObj():
    obj = ArrayLikeObj()
    # create simple coordmap
    xform = np.eye(4)
    affine = Affine(xform)
    coordmap = CoordinateMap.from_affine('xyz', 'ijk', affine,
                                    (2,3,4))
    # create image form array-like object and coordmap
    img = image.Image(obj, coordmap)
    assert img.ndim == 3
    assert img.shape == (2,3,4)
    assert np.allclose(np.asarray(img), 1)
    assert np.allclose(img[:], 1)
    img[:] = 4
    assert np.allclose(img[:], 4)

# Should test common image sizes 2D, 3D, 4D
class TestFromArray(TestCase):
    def setUp(self):
        self.array2D_shape = (2,3)
        self.array3D_shape = (2,3,4)
        self.array4D_shape = (2,3,4,5)

    def test_defaults_2D(self):
        data = np.ones(self.array2D_shape)
        img = image.fromarray(data, names=['yspace', 'xspace'])
        assert isinstance(img._data, np.ndarray)
        assert img.ndim == 2
        assert img.shape == self.array2D_shape
        self.assertRaises(AttributeError, getattr, img, 'header')
        assert img.affine.shape == (3,3)
        assert img.affine.diagonal().all() == 1
        
    def test_defaults_3D(self):
        img = image.fromarray(np.ones(self.array3D_shape))
        assert isinstance(img._data, np.ndarray)
        assert img.ndim == 3
        assert img.shape == self.array3D_shape
        # ndarray's do not have a header
        self.assertRaises(AttributeError, getattr, img, 'header')
        assert img.affine.shape == (4,4)
        assert img.affine.diagonal().all() == 1

    def test_defaults_4D(self):
        data = np.ones(self.array4D_shape)
        names = ['time', 'zspace', 'yspace', 'xspace']
        img = image.fromarray(data, names=names)
        assert isinstance(img._data, np.ndarray)
        assert img.ndim == 4
        assert img.shape == self.array4D_shape
        self.assertRaises(AttributeError, getattr, img, 'header')
        assert img.affine.shape == (5,5)
        assert img.affine.diagonal().all() == 1




