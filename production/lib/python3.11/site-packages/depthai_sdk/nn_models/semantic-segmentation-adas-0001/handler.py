import numpy as np
import depthai as dai
from depthai_sdk.classes.packets import SemanticSegmentation


def decode(nndata: dai.NNData):
    [print(f"Layer name: {l.name}, Type: {l.dataType}, Dimensions: {l.dims}") for l in data.getAllLayers()]
    # after squeeze the data.shape is 4,512, 896
    # output = np.squeeze(nndata.getLayerFp16('L0317_ReWeight_SoftMax'))
    # # Output is an array of 4x512x896 == 1835008 bytes, and has values from 0 to 1
    # output = output.reshape((4, 512, 896))
    # classes = np.asarray([0, 1, 2, 3], dtype=np.uint8)
    # indices = np.argmax(output, axis=0)
    # outputMap = np.take(classes, indices, axis=0)
    # return SemanticSegmentation(nndata, mask=outputMap)

