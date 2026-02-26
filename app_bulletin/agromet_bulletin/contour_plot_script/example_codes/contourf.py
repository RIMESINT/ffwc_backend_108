{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "a37c9fae",
   "metadata": {},
   "outputs": [
    {
     "ename": "",
     "evalue": "",
     "output_type": "error",
     "traceback": [
      "\u001b[1;31mRunning cells with 'venv' requires the ipykernel package.\n",
      "\u001b[1;31mRun the following command to install 'ipykernel' into the Python environment. \n",
      "\u001b[1;31mCommand: '/home/shifullah/SHIFULLAH/Official_Project/Sesame/Project/rimes_sesame_backend/venv/bin/python -m pip install ipykernel -U --force-reinstall'"
     ]
    }
   ],
   "source": [
    "from netCDF4 import Dataset, num2date\n",
    "\n",
    "import numpy as np\n",
    "import matplotlib.pyplot as plt\n",
    "from cartopy import crs as ccrs\n",
    "from cartopy import feature as cfeature"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "47a60493",
   "metadata": {},
   "outputs": [
    {
     "ename": "",
     "evalue": "",
     "output_type": "error",
     "traceback": [
      "\u001b[1;31mRunning cells with 'venv' requires the ipykernel package.\n",
      "\u001b[1;31mRun the following command to install 'ipykernel' into the Python environment. \n",
      "\u001b[1;31mCommand: '/home/shifullah/SHIFULLAH/Official_Project/Sesame/Project/rimes_sesame_backend/venv/bin/python -m pip install ipykernel -U --force-reinstall'"
     ]
    }
   ],
   "source": [
    "# nf = Dataset('/RIMESNAS/ECMWF_HRES/01012023.nc','r')\n",
    "nf = Dataset('/RIMESNAS/ECMWF_HRES/01012023.nc','r')"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "b965ec7d",
   "metadata": {
    "collapsed": true,
    "jupyter": {
     "outputs_hidden": true
    }
   },
   "outputs": [
    {
     "ename": "",
     "evalue": "",
     "output_type": "error",
     "traceback": [
      "\u001b[1;31mRunning cells with 'venv' requires the ipykernel package.\n",
      "\u001b[1;31mRun the following command to install 'ipykernel' into the Python environment. \n",
      "\u001b[1;31mCommand: '/home/shifullah/SHIFULLAH/Official_Project/Sesame/Project/rimes_sesame_backend/venv/bin/python -m pip install ipykernel -U --force-reinstall'"
     ]
    }
   ],
   "source": [
    "!ncdump -h /RIMESNAS/ECMWF_HRES/01012023.nc"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "53a7c91c",
   "metadata": {},
   "outputs": [
    {
     "ename": "",
     "evalue": "",
     "output_type": "error",
     "traceback": [
      "\u001b[1;31mRunning cells with 'venv' requires the ipykernel package.\n",
      "\u001b[1;31mRun the following command to install 'ipykernel' into the Python environment. \n",
      "\u001b[1;31mCommand: '/home/shifullah/SHIFULLAH/Official_Project/Sesame/Project/rimes_sesame_backend/venv/bin/python -m pip install ipykernel -U --force-reinstall'"
     ]
    }
   ],
   "source": [
    "lat = nf.variables['latitude'][:]\n",
    "lon = nf.variables['longitude'][:]\n",
    "\n",
    "time = num2date(nf.variables['time'][:], nf.variables['time'].units)\n",
    "\n",
    "pr =  (nf.variables['cp'][:] +  nf.variables['lsp'][:] ) * 1000\n",
    "t2 =  nf.variables['t2m'][:] - 273.15"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "98a10886",
   "metadata": {},
   "outputs": [
    {
     "ename": "",
     "evalue": "",
     "output_type": "error",
     "traceback": [
      "\u001b[1;31mRunning cells with 'venv' requires the ipykernel package.\n",
      "\u001b[1;31mRun the following command to install 'ipykernel' into the Python environment. \n",
      "\u001b[1;31mCommand: '/home/shifullah/SHIFULLAH/Official_Project/Sesame/Project/rimes_sesame_backend/venv/bin/python -m pip install ipykernel -U --force-reinstall'"
     ]
    }
   ],
   "source": [
    "0 1 1 2\n",
    "\n",
    "0 1 2 4"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "c2747389",
   "metadata": {},
   "outputs": [
    {
     "ename": "",
     "evalue": "",
     "output_type": "error",
     "traceback": [
      "\u001b[1;31mRunning cells with 'venv' requires the ipykernel package.\n",
      "\u001b[1;31mRun the following command to install 'ipykernel' into the Python environment. \n",
      "\u001b[1;31mCommand: '/home/shifullah/SHIFULLAH/Official_Project/Sesame/Project/rimes_sesame_backend/venv/bin/python -m pip install ipykernel -U --force-reinstall'"
     ]
    }
   ],
   "source": [
    "time[:21]"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "7964b664",
   "metadata": {
    "collapsed": true,
    "jupyter": {
     "outputs_hidden": true
    }
   },
   "outputs": [
    {
     "ename": "",
     "evalue": "",
     "output_type": "error",
     "traceback": [
      "\u001b[1;31mRunning cells with 'venv' requires the ipykernel package.\n",
      "\u001b[1;31mRun the following command to install 'ipykernel' into the Python environment. \n",
      "\u001b[1;31mCommand: '/home/shifullah/SHIFULLAH/Official_Project/Sesame/Project/rimes_sesame_backend/venv/bin/python -m pip install ipykernel -U --force-reinstall'"
     ]
    }
   ],
   "source": [
    "for i,v in enumerate(time):\n",
    "    print(i,v)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "48b84bd6",
   "metadata": {},
   "outputs": [
    {
     "ename": "",
     "evalue": "",
     "output_type": "error",
     "traceback": [
      "\u001b[1;31mRunning cells with 'venv' requires the ipykernel package.\n",
      "\u001b[1;31mRun the following command to install 'ipykernel' into the Python environment. \n",
      "\u001b[1;31mCommand: '/home/shifullah/SHIFULLAH/Official_Project/Sesame/Project/rimes_sesame_backend/venv/bin/python -m pip install ipykernel -U --force-reinstall'"
     ]
    }
   ],
   "source": []
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "e3acef1b",
   "metadata": {},
   "outputs": [
    {
     "ename": "",
     "evalue": "",
     "output_type": "error",
     "traceback": [
      "\u001b[1;31mRunning cells with 'venv' requires the ipykernel package.\n",
      "\u001b[1;31mRun the following command to install 'ipykernel' into the Python environment. \n",
      "\u001b[1;31mCommand: '/home/shifullah/SHIFULLAH/Official_Project/Sesame/Project/rimes_sesame_backend/venv/bin/python -m pip install ipykernel -U --force-reinstall'"
     ]
    }
   ],
   "source": [
    "pr_1_5_day = pr[20, :, :]\n",
    "pr_6_10_day = pr[-1, :, :] - pr_1_5_day"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "75b40c01",
   "metadata": {},
   "outputs": [
    {
     "ename": "",
     "evalue": "",
     "output_type": "error",
     "traceback": [
      "\u001b[1;31mRunning cells with 'venv' requires the ipykernel package.\n",
      "\u001b[1;31mRun the following command to install 'ipykernel' into the Python environment. \n",
      "\u001b[1;31mCommand: '/home/shifullah/SHIFULLAH/Official_Project/Sesame/Project/rimes_sesame_backend/venv/bin/python -m pip install ipykernel -U --force-reinstall'"
     ]
    }
   ],
   "source": [
    "t2.shape"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "5f65fa1f",
   "metadata": {},
   "outputs": [
    {
     "ename": "",
     "evalue": "",
     "output_type": "error",
     "traceback": [
      "\u001b[1;31mRunning cells with 'venv' requires the ipykernel package.\n",
      "\u001b[1;31mRun the following command to install 'ipykernel' into the Python environment. \n",
      "\u001b[1;31mCommand: '/home/shifullah/SHIFULLAH/Official_Project/Sesame/Project/rimes_sesame_backend/venv/bin/python -m pip install ipykernel -U --force-reinstall'"
     ]
    }
   ],
   "source": [
    "tmax_1_5_day = np.amax( t2[:21], axis=0 )\n",
    "tmax_6_10_day = np.amax( t2[21:], axis=0 )"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "e99c096c",
   "metadata": {},
   "outputs": [
    {
     "ename": "",
     "evalue": "",
     "output_type": "error",
     "traceback": [
      "\u001b[1;31mRunning cells with 'venv' requires the ipykernel package.\n",
      "\u001b[1;31mRun the following command to install 'ipykernel' into the Python environment. \n",
      "\u001b[1;31mCommand: '/home/shifullah/SHIFULLAH/Official_Project/Sesame/Project/rimes_sesame_backend/venv/bin/python -m pip install ipykernel -U --force-reinstall'"
     ]
    }
   ],
   "source": [
    "tmax_1_5_day"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "b043009b",
   "metadata": {},
   "outputs": [
    {
     "ename": "",
     "evalue": "",
     "output_type": "error",
     "traceback": [
      "\u001b[1;31mRunning cells with 'venv' requires the ipykernel package.\n",
      "\u001b[1;31mRun the following command to install 'ipykernel' into the Python environment. \n",
      "\u001b[1;31mCommand: '/home/shifullah/SHIFULLAH/Official_Project/Sesame/Project/rimes_sesame_backend/venv/bin/python -m pip install ipykernel -U --force-reinstall'"
     ]
    }
   ],
   "source": [
    "lat_m = (lat >= 22) & (lat <= 42)\n",
    "lon_m = (lon>=27) & (lon<=32)\n",
    "\n",
    "m2d= np.ix_(lat_m, lon_m)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "0a603e1b",
   "metadata": {},
   "outputs": [
    {
     "ename": "",
     "evalue": "",
     "output_type": "error",
     "traceback": [
      "\u001b[1;31mRunning cells with 'venv' requires the ipykernel package.\n",
      "\u001b[1;31mRun the following command to install 'ipykernel' into the Python environment. \n",
      "\u001b[1;31mCommand: '/home/shifullah/SHIFULLAH/Official_Project/Sesame/Project/rimes_sesame_backend/venv/bin/python -m pip install ipykernel -U --force-reinstall'"
     ]
    }
   ],
   "source": [
    "fig = plt.figure(dpi=300)\n",
    "# ax = plt.axes(ccrs.PlateCarree())\n",
    "cf = plt.contourf(lon[lon_m],lat[lat_m], tmax_1_5_day[m2d])"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.10.6"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
