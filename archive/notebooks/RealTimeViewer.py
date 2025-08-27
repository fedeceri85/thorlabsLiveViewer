# %%
import os
import gc
import sys
import matplotlib.pyplot as plt
import threading
import time
import numpy as np

 #from scipy.ndimage import gaussian_filter
if sys.platform!='darwin':
    from cupyx.scipy.ndimage import gaussian_filter
    import cupy as cp
else:
    from scipy.ndimage import gaussian_filter
    import pyclesperanto_prototype as cle
    # initialize GPU
    device = cle.select_device("GTX")
    print("Used GPU: ", device)
 

import numpy as np
from os.path import getsize
import napari
from skimage.io import imread

filename =  'Image_001_001.raw'
previewFilename = 'ChanC_Preview.tif'
MAXCHUNKSIZE = 1024*288*2*3
class thorlabsFile():
   
    def __init__(self,folder) -> None:

        self.folder = folder
        self.fullpath = os.path.join(self.folder,filename)

        prev = imread(os.path.join(self.folder,previewFilename))

        self.width = prev.shape[1] 
        self.height = prev.shape[0]

        self.r = open(self.fullpath,'rb')
        nbytes = getsize(self.fullpath)
        self.frameSize = self.width*self.height*2
        self.nFrames = int(nbytes/self.frameSize)

        self.currentLastFrame = 0

        self.array = np.empty((0,self.height,self.width),dtype=np.uint16)
        self.app = napari.Viewer()
        

        #self.app.add_image(self.array)

    def loadFile(self,folder):

        try:
            self.r.close()
        except:
            pass
        
        self.folder = folder
        self.fullpath = os.path.join(self.folder,filename)
        prev = imread(os.path.join(self.folder,previewFilename))

        self.width = prev.shape[1] 
        self.height = prev.shape[0]

        self.r = open(self.fullpath,'rb')
        nbytes = getsize(self.fullpath)
        self.frameSize = self.width*self.height*2
        self.nFrames = int(nbytes/self.frameSize)

        self.currentLastFrame = 0

        self.array = np.empty((0,self.height,self.width),dtype=np.uint16)

        l = self.app.layers['Image']
        
        l.data = self.array
        
    def getImage(self,n):

        offset = n*self.frameSize
        self.r.seek(offset)
        st = self.r.read(self.frameSize)
        nparray = np.frombuffer(st,dtype = np.uint16).reshape((1,self.height,self.width))
        
        return nparray

    def loadWholeStack(self,start=0,end=-1,step=1):

        
        if end == -1:
            end = nFrames
        totalFrames = end-start
        totalFramesSize = totalFrames*self.frameSize

        if totalFramesSize<=MAXCHUNKSIZE:
            #stack = np.zeros((self.height,self.width,totalSize),dtype=np.uint16)
            #for i in range(start,end,step):
            #    stack[:,:,i-start] = gaussian_filter(self.getImage(i),2)
            #    #stack.append(getImage(r,i,width,height))

            offset = start*self.frameSize
            self.r.seek(offset)
            st = self.r.read(totalFramesSize)
            
            if sys.platform != 'darwin':
                stack = cp.frombuffer(st,dtype = np.uint16).reshape((totalFrames,self.height,self.width))
                stack = stack[::,:,:]
                stack = gaussian_filter(stack,(2,2,2))
                stack3 = [cp.asnumpy(stack)]
            else:
                stack = np.frombuffer(st,dtype = np.uint16).reshape((totalFrames,self.height,self.width))
                stack = stack[::2,:,:]
                stack = cle.gaussian_blur(stack,sigma_x=2,sigma_y=2,sigma_z=2).astype(np.uint16)
                stack3 = [stack]


            
        else:
            chunksizeFrames = MAXCHUNKSIZE//(self.frameSize)  #number of frames in a chunk
            nchunks = totalFrames//chunksizeFrames
            remainderFrames = totalFrames%chunksizeFrames
            stack3 = []
            for i in range(nchunks):
                offset = (start+i*chunksizeFrames)*self.frameSize
                self.r.seek(offset)
                st = self.r.read(self.frameSize*chunksizeFrames)
                if sys.platform !='darwin':
                    stack = cp.frombuffer(st,dtype = np.uint16).reshape((chunksizeFrames,self.height,self.width))
                    stack = stack[::,:,:]
                    stack = gaussian_filter(stack,(2,2,2))
                    stack3.append(cp.asnumpy(stack))
                else:
                    stack = np.frombuffer(st,dtype = np.uint16).reshape((chunksizeFrames,self.height,self.width))
                    stack = stack[::2,:,:]
                    stack = cle.gaussian_blur(stack,sigma_x=2,sigma_y=2,sigma_z=2).astype(np.uint16)
                    stack3.append(stack)

            if remainderFrames != 0:
                offset = (start+nchunks*chunksizeFrames)*self.frameSize
                self.r.seek(offset)
                st = self.r.read(self.frameSize*remainderFrames)
                if sys.platform != 'darwin':
                    stack = cp.frombuffer(st,dtype = np.uint16).reshape((remainderFrames,self.height,self.width))
                    stack = stack[::,:,:]
                    stack = gaussian_filter(stack,(2,2,2))
                    stack3.append(cp.asnumpy(stack))
                else:
                    stack = np.frombuffer(st,dtype = np.uint16).reshape((remainderFrames,self.height,self.width))
                    stack = stack[::,:,:]
                    stack = cle.gaussian_blur(stack,sigma_x=2,sigma_y=2,sigma_z=2).astype(np.uint16)
                    stack3.append(stack) 
        if sys.platform !='darwin':         
            cp._default_memory_pool.free_all_blocks()    
        return stack3

    def loadNextNFrames(self,n):
        newStacks = self.loadWholeStack(start=self.currentLastFrame,end = self.currentLastFrame+n)
        self.array= np.vstack([self.array, *newStacks])
        del newStacks
        try:
            l = self.app.layers['Image']
            l.data = self.array
        except:
            self.app.add_image(self.array)
            self.app.add_shapes(None, shape_type='rectangle', name='Shapes',  edge_width=3, face_color=np.array([0,0,0,0]),edge_color = 'red',edge_color_cycle=plt.rcParams['axes.prop_cycle'].by_key()['color'])


        self.currentLastFrame = self.array.shape[0]

    def loadUpToFrameN(self,n):
        
        if (n<self.currentLastFrame) | (n>self.nFrames):
            return
        newStack = self.loadWholeStack(start=self.currentLastFrame,end = n)
        self.array= np.vstack([self.array, *newStack])

        if self.currentLastFrame == 0:
                self.app.add_image(self.array)
                self.app.add_shapes(None, shape_type='rectangle', name='Shapes',  edge_width=3, face_color=np.array([0,0,0,0]),edge_color = 'red',edge_color_cycle=plt.rcParams['axes.prop_cycle'].by_key()['color'])
        else:
            l = self.app.layers['Image']
            l.data = self.array
        self.currentLastFrame = self.array.shape[0]

    def start_live_stream(self, chunk_size=3, update_interval=10):
        """
        Start a background thread that periodically loads new frames.
        Stops when the first all-zero frame is encountered.
        """
        stop_flag = threading.Event()

        def loop():
            while not stop_flag.is_set():
                # Load a chunk of frames
                newStacks = self.loadUpToFrameN(self.currentLastFrame + chunk_size)
                if not newStacks:
                    time.sleep(update_interval)
                    continue

                # concatenate GPU/CPU blocks into one numpy stack
                new_block = np.vstack(newStacks)

                # check for all-zero frames and truncate there
                zero_idx = None
                for i, fr in enumerate(new_block):
                    if np.all(fr == 0):
                        zero_idx = i
                        break

                if zero_idx is not None:
                    # Only keep frames up to the first zero
                    new_block = new_block[:zero_idx]
                    stop_flag.set()  # stop loop after this append

                if new_block.size > 0:
                    self.array = np.vstack([self.array, new_block])
                    try:
                        l = self.app.layers['Image']
                        l.data = self.array
                    except KeyError:
                        self.app.add_image(self.array)
                        self.app.add_shapes(
                            None, shape_type='rectangle', name='Shapes',
                            edge_width=3, face_color=np.array([0,0,0,0]),
                            edge_color='red',
                            edge_color_cycle=plt.rcParams['axes.prop_cycle'].by_key()['color']
                        )
                    self.currentLastFrame = self.array.shape[0]

                time.sleep(update_interval)

        thread = threading.Thread(target=loop, daemon=True)
        thread.start()
        napari.run()
        stop_flag.set()

# %%
tb = thorlabsFile('../sampleImage')

# %%

tb.start_live_stream(chunk_size=1, update_interval=1)

# %%
def divide(a, b):
    breakpoint()   # execution will stop here
    return a / b

result = divide(10, 0)  # wi    ll trigger ZeroDivisionError and drop you into the debugger

# %%
from IPython.core.debugger import set_trace

def divide(a, b):

    return a / b

result = divide(10, 0)

# %%
%debug

# %%



