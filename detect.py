# Copyright (C) 2021  Alexey Shkarin

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import sys
if __name__=="__main__":
    os.chdir(os.path.join(".",os.path.split(sys.argv[0])[0]))
    sys.path.append(".")  # set current folder to the file location and add it to the search path

from pylablib.devices import Andor, DCAM, IMAQdx, IMAQ, PhotonFocus, SiliconSoftware, PCO, uc480, Thorlabs
from pylablib.core.utils import dictionary
from pylablib.core.fileio.loadfile import load_dict
from pylablib.core.fileio.savefile import save_dict
import pylablib

import argparse


def print_added_camera(name, desc):
    """Print information about a newly detected camera"""
    print("Adding camera under name {}:".format(name))
    print("\tkind = '{}'".format(desc["kind"]))
    if "params" in desc:
        print("\tparams = '{}'".format(desc["params"].as_dict()))
    if "display_name" in desc:
        print("\tdisplay_name = '{}'".format(desc["display_name"]))
    print("")


def detect_AndorSDK2(verbose=False):
    if verbose: print("Searching for Andor SDK2 cameras")
    cameras=dictionary.Dictionary()
    try:
        cam_num=Andor.get_cameras_number_SDK2()
    except (Andor.AndorError, OSError):
        if verbose: print("Error loading or running the Andor SDK2 library: required software (Andor Solis) must be missing\n")
        return cameras
    if cam_num==0:
        if verbose: print("Found no Andor SDK2 cameras\n")
        return cameras
    if verbose: print("Found {} Andor SDK2 camera{}".format(cam_num,"s" if cam_num>1 else ""))
    for i in range(cam_num):
        try:
            if verbose: print("Checking Andor SDK2 camera idx={}".format(i))
            with Andor.AndorSDK2Camera(idx=i) as cam:
                cam_desc=dictionary.Dictionary({"params/idx":i})
                cap=cam.get_capabilities()
                device_info=cam.get_device_info()
                if verbose: print("\tModel {}".format(device_info.head_model))
                if cap["cam_type"]=="AC_CAMERATYPE_IXON":
                    cam_desc["kind"]="AndorSDK2IXON"
                elif cap["cam_type"]=="AC_CAMERATYPE_LUCA":
                    cam_desc["kind"]="AndorSDK2Luca"
                else:
                    cam_desc["kind"]="AndorSDK2"
            cam_desc["display_name"]="Andor {} {}".format(device_info.head_model,device_info.serial_number)
            cam_name="andor_{}".format(i)
            cameras[cam_name]=cam_desc
            if verbose: print_added_camera(cam_name,cam_desc)
        except Andor.AndorError:
            pass
    return cameras

def detect_AndorSDK3(verbose=False):
    if verbose: print("Searching for Andor SDK3 cameras")
    cameras=dictionary.Dictionary()
    try:
        cam_num=Andor.get_cameras_number_SDK3()
    except (Andor.AndorError, OSError):
        if verbose: print("Error loading or running the Andor SDK3 library: required software (Andor Solis) must be missing\n")
        return cameras
    if cam_num==0:
        if verbose: print("Found no Andor SDK3 cameras\n")
        return cameras
    if verbose: print("Found {} Andor SDK3 camera{}".format(cam_num,"s" if cam_num>1 else ""))
    for i in range(cam_num):
        try:
            if verbose: print("Checking Andor SDK3 camera idx={}".format(i))
            with Andor.AndorSDK3Camera(idx=i) as cam:
                cam_desc=dictionary.Dictionary({"params/idx":i})
                device_info=cam.get_device_info()
                if verbose: print("\tModel {}".format(device_info.camera_model))
                if device_info.camera_model.lower().startswith("zyla"):
                    cam_desc["kind"]="AndorSDK3Zyla"
                else:
                    cam_desc["kind"]="AndorSDK3"
            cam_desc["display_name"]="Andor {} {}".format(device_info.camera_model,device_info.serial_number)
            cam_name="andor_sdk3_{}".format(i)
            cameras[cam_name]=cam_desc
            if verbose: print_added_camera(cam_name,cam_desc)
        except Andor.AndorError:
            pass
    return cameras

def detect_DCAM(verbose=False):
    if verbose: print("Searching for DCAM cameras")
    cameras=dictionary.Dictionary()
    try:
        cam_num=DCAM.get_cameras_number()
    except (DCAM.DCAMError, OSError):
        if verbose: print("Error loading or running the DCAM library: required software (Hamamtsu HOKAWO or DCAM API) must be missing\n")
        return cameras
    if cam_num==0:
        if verbose: print("Found no DCAM cameras\n")
        return cameras
    if verbose: print("Found {} DCAM camera{}".format(cam_num,"s" if cam_num>1 else ""))
    for i in range(cam_num):
        try:
            if verbose: print("Checking DCAM camera idx={}".format(i))
            with DCAM.DCAMCamera(idx=i) as cam:
                cam_desc=dictionary.Dictionary({"params/idx":i})
                device_info=cam.get_device_info()
                if verbose: print("\tVendor {}, model {}".format(device_info.vendor,device_info.model))
                if device_info.model.lower().startswith("c11440"):
                    cam_desc["kind"]="DCAMOrca"
                elif device_info.model.lower().startswith("c9100"):
                    cam_desc["kind"]="DCAMImagEM"
                else:
                    cam_desc["kind"]="DCAM"
            cam_desc["display_name"]="{} {}".format(device_info.model,device_info.serial_number)
            cam_name="dcam_{}".format(i)
            cameras[cam_name]=cam_desc
            if verbose: print_added_camera(cam_name,cam_desc)
        except DCAM.DCAMError:
            pass
    return cameras

def detect_IMAQdx(verbose=False):
    if verbose: print("Searching for IMAQdx cameras")
    cameras=dictionary.Dictionary()
    try:
        cams=IMAQdx.list_cameras()
    except (IMAQdx.IMAQdxError, OSError, AttributeError):
        if verbose: print("Error loading or running the IMAQdx library: required software (NI IMAQdx) must be missing\n")
        return cameras
    if len(cams)==0:
        if verbose: print("Found no IMAQdx cameras\n")
        return cameras
    cam_num=len(cams)
    if verbose: print("Found {} IMAQdx camera{}".format(cam_num,"s" if cam_num>1 else ""))
    for i,cdesc in enumerate(cams):
        cam_desc=dictionary.Dictionary({"params/name":cdesc.name})
        if verbose: print("Checking IMAQdx camera idx={}\n\tVendor {},   model {}".format(i,cdesc.vendor,cdesc.model))
        if cdesc.vendor.lower().startswith("photonfocus") and cdesc.model.startswith("HD1"):
            cam_desc["kind"]="PhotonFocusLAN"
        else:
            if verbose: print("No control for this camera\n")
            continue
        cam_desc["display_name"]="{} {}".format(cdesc.vendor,cdesc.model)
        cam_name="imaqdx_{}".format(i)
        cameras[cam_name]=cam_desc
        if verbose: print_added_camera(cam_name,cam_desc)
    return cameras

def detect_PhotonFocus(verbose=False):
    if verbose: print("Searching for PhotonFocus cameras (might take several minutes)")
    cameras=dictionary.Dictionary()
    try:
        imaq_cams=IMAQ.list_cameras()
    except (IMAQ.IMAQError, OSError):
        imaq_cams=[]
        if verbose: print("Error loading or running the IMAQ library: required software (NI IMAQ) must be missing\n")
    try:
        siso_boards=SiliconSoftware.list_boards()
    except (SiliconSoftware.SiliconSoftwareError, OSError):
        siso_boards=[]
        if verbose: print("Error loading or running the Silicon Software library: required software (Silicon Software Runtime Environment) must be missing\n")
    try:
        pf_cams=PhotonFocus.list_cameras(only_supported=False)
    except (PhotonFocus.PFCamError, OSError):
        if verbose: print("Error loading or running the PFCam library: required software (PhotonFocus PFRemote) must be missing\n")
        return cameras
    pf_cams=[(p,d) for (p,d) in pf_cams if d.manufacturer!="RS-232"]  # these usually don't have cameras, but can lead to very long polling times
    if len(pf_cams)==0:
        if verbose: print("Found no PhotonFocus cameras\n")
        return cameras
    if verbose: print("Checking potential PFRemote interfaces {}\n".format(", ".join(["{}/{}".format(d.manufacturer,d.port) for _,d in pf_cams])))
    cams=[]
    for p,cdesc in pf_cams:
        print("Checking interface {}/{} ... ".format(cdesc.manufacturer,cdesc.port),end="")
        name=PhotonFocus.query_camera_name(p)
        if name is not None:
            print("discovered camera {}".format(name))
            cams.append((p,cdesc))
        else:
            print("not a camera")
    cam_num=len(cams)
    if verbose: print("Found {} PhotonFocus camera{}".format(cam_num,"s" if cam_num>1 else ""))
    for p,cdesc in cams:
        cam_name=None
        pfcam_port=(cdesc.manufacturer,cdesc.port)
        name=PhotonFocus.query_camera_name(p)
        cam_desc=dictionary.Dictionary({"params/pfcam_port":pfcam_port})
        cam_desc["display_name"]="{} port {}".format(name,p)
        if verbose: print("Checking PhotonFocus camera idx={}\n\tPort {},   vendor {},   model {}".format(p,cdesc.port,cdesc.manufacturer,name))
        selidx=None
        for i,fg in enumerate(imaq_cams):
            try:
                cam=PhotonFocus.PhotonFocusIMAQCamera(imaq_name=fg,pfcam_port=pfcam_port)
            except PhotonFocus.PhotonFocusIMAQCamera.Error:
                continue
            try:
                if PhotonFocus.check_grabber_association(cam):
                    selidx=i
                    break
            except PhotonFocus.PhotonFocusIMAQCamera.Error:
                pass
            finally:
                cam.close()
        if selidx is not None:
            cam_name="ppimaq_{}".format(p)
            cam_desc["kind"]="PhotonFocusIMAQ"
            cam_desc["params/imaq_name"]=imaq_cams.pop(selidx)
        if "kind" not in cam_desc:
            for i,fg in enumerate(siso_boards):
                applets=SiliconSoftware.list_applets(i)
                app=None
                if any(a.name=="DualAreaGray16" for a in applets):
                    app="DualAreaGray16"
                    ports=[0,1]
                elif any(a.name=="SingleAreaGray16" for a in applets):
                    app="SingleAreaGray16"
                    ports=[0]
                else:
                    continue
                selp=None
                for p in ports:
                    try:
                        cam=PhotonFocus.PhotonFocusSiSoCamera(siso_board=i,siso_applet=app,siso_port=p,pfcam_port=pfcam_port)
                    except PhotonFocus.PhotonFocusSiSoCamera.Error:
                        continue
                    try:
                        if PhotonFocus.check_grabber_association(cam):
                            selp=p
                            break
                    except PhotonFocus.PhotonFocusSiSoCamera.Error:
                        pass
                    finally:
                        cam.close()
                if selp is not None:
                    cam_desc["kind"]="PhotonFocusSiSo"
                    cam_name="ppsiso_{}".format(p)
                    cam_desc["params/siso_board"]=i
                    cam_desc["params/siso_applet"]=app
                    cam_desc["params/siso_port"]=selp
                    break
        if cam_name is not None:
            cameras[cam_name]=cam_desc
            if verbose: print_added_camera(cam_name,cam_desc)
    return cameras

def detect_PCO(verbose=False):
    if verbose: print("Searching for PCO cameras")
    cameras=dictionary.Dictionary()
    try:
        cam_num=PCO.get_cameras_number()
    except (PCO.PCOSC2Error, OSError):
        if verbose: print("Error loading or running the PCO SC2 library: required software (PCO SDK) must be missing\n")
        return cameras
    if cam_num==0:
        if verbose: print("Found no PCO cameras\n")
        return cameras
    if verbose: print("Found {} PCO camera{}".format(cam_num,"s" if cam_num>1 else ""))
    for i in range(cam_num):
        try:
            if verbose: print("Checking PCO camera idx={}".format(i))
            with PCO.PCOSC2Camera(idx=i) as cam:
                cam_desc=dictionary.Dictionary({"params/idx":i,"kind":"PCOSC2"})
                device_info=cam.get_device_info()
                if verbose: print("\tModel {}, serial number {}".format(device_info.model,device_info.serial_number))
            cam_desc["display_name"]="{} {}".format(device_info.model,device_info.serial_number)
            cam_name="pcosc2_{}".format(i)
            cameras[cam_name]=cam_desc
            if verbose: print_added_camera(cam_name,cam_desc)
        except PCO.PCOSC2Error:
            pass
    return cameras

def detect_uc480(verbose=False, backend="uc480"):
    if verbose: print("Searching for {} cameras".format("Thorlabs uc480" if backend=="uc480" else "IDS uEye"))
    cameras=dictionary.Dictionary()
    try:
        cam_infos=uc480.list_cameras(backend=backend)
    except (uc480.uc480Error, OSError):
        if verbose: print("Error loading or running {} library: required software ({}) must be missing\n".format(backend,("ThorCam" if backend=="uc480" else "IDS uEye")))
        return cameras
    cam_num=len(cam_infos)
    if not cam_num:
        if verbose: print("Found no {} cameras\n".format(backend))
        return cameras
    if verbose: print("Found {} {} camera{}".format(cam_num,backend,"s" if cam_num>1 else ""))
    for c in cam_infos:
        idx=c.cam_id
        dev_idx=c.dev_id
        sn=c.serial_number
        if verbose: print("Checking {} camera dev_idx={}, cam_idx={}".format(backend,dev_idx,idx))
        if verbose: print("\tModel {}, serial {}".format(c.model,sn))
        cam_desc=dictionary.Dictionary({"params/idx":idx,"params/dev_idx":dev_idx,"params/sn":sn,"params/backend":backend,"kind":"UC480"})
        cam_desc["display_name"]="{} {}".format(c.model,c.serial_number)
        cam_name="{}_{}".format(backend,idx)
        cameras[cam_name]=cam_desc
        if verbose: print_added_camera(cam_name,cam_desc)
    return cameras

def detect_ThorlabsTLCam(verbose=False):
    if verbose: print("Searching for Thorlabs TSI cameras")
    cameras=dictionary.Dictionary()
    try:
        cam_infos=Thorlabs.list_cameras_tlcam()
    except (Thorlabs.ThorlabsTLCameraError, OSError):
        if verbose: print("Error loading or running the Thorlabs TSI library: required software (ThorCam) must be missing\n")
        return cameras
    cam_num=len(cam_infos)
    if not cam_num:
        if verbose: print("Found no Thorlabs TLCam cameras\n")
        return cameras
    if verbose: print("Found {} Thorlabs TLCam camera{}".format(cam_num,"s" if cam_num>1 else ""))
    for s in cam_infos:
        if verbose: print("Checking Thorlabs TSI camera serial={}".format(s))
        cam_desc=dictionary.Dictionary({"params/serial":s,"kind":"ThorlabsTLCam"})
        with Thorlabs.ThorlabsTLCamera(s) as cam:
            device_info=cam.get_device_info()
        cam_desc["display_name"]="{} {}".format(device_info.model,device_info.serial_number)
        cam_name="ThorlabsTLCam_{}".format(s)
        cameras[cam_name]=cam_desc
        if verbose: print_added_camera(cam_name,cam_desc)
    return cameras


def detect_all(verbose=False):
    cams=dictionary.Dictionary()
    cams.merge(detect_AndorSDK2(verbose=verbose),"cameras")
    cams.merge(detect_AndorSDK3(verbose=verbose),"cameras")
    cams.merge(detect_DCAM(verbose=verbose),"cameras")
    cams.merge(detect_IMAQdx(verbose=verbose),"cameras")
    cams.merge(detect_PhotonFocus(verbose=verbose),"cameras")
    cams.merge(detect_PCO(verbose=verbose),"cameras")
    cams.merge(detect_uc480(verbose=verbose,backend="uc480"),"cameras")
    cams.merge(detect_uc480(verbose=verbose,backend="ueye"),"cameras")
    cams.merge(detect_ThorlabsTLCam(verbose=verbose),"cameras")
    if "cameras" in cams:
        for c in cams["cameras"]:
            if "display_name" not in cams["cameras",c]:
                cams["cameras",c,"display_name"]=c
    return cams


def update_settings_file(cfg_path="settings.cfg", verbose=False, confirm=False):
    settings=detect_all(verbose=verbose)
    if not settings:
        if verbose:
            print("Couldn't detect any supported cameras")
    else:
        do_save=True
        if os.path.exists(cfg_path):
            ans=input("Configuration file already exists. Modify? [y/N] ").strip() if confirm else "y"
            if ans.lower()!="y":
                do_save=False
            else:
                curr_settings=load_dict(cfg_path)
                if "cameras" in curr_settings:
                    del curr_settings["cameras"]
                curr_settings["cameras"]=settings["cameras"]
                settings=curr_settings
        if do_save:
            save_dict(settings,cfg_path)
            if verbose:
                print("Successfully generated config file {}".format(cfg_path))
        else:
            return
    if confirm and not do_save:
        input()

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="Camera autodetection")
    parser.add_argument("--silent","-s",help="silent execution",action="store_true")
    parser.add_argument("--yes","-y",help="automatically confirm settings file overwrite",action="store_true")
    parser.add_argument("--config-file","-cf", help="configuration file path",metavar="FILE",default="settings.cfg")
    args=parser.parse_args()
    if os.path.exists(args.config_file):
        settings=load_dict(args.config_file)
        if "dlls" in settings:
            for k,v in settings["dlls"].items():
                pylablib.par["devices/dlls",k]=v
    update_settings_file(cfg_path=args.config_file,verbose=not args.silent,confirm=not (args.silent or args.yes))