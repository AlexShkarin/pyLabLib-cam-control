from . import base

from pylablib.core.thread import controller
from pylablib.core.utils import net, dictionary, general, py3
from pylablib.thread.stream.stream_message import FramesAccumulator
from pylablib.thread.stream.stream_manager import StreamIDCounter

import numpy as np
import json



class IncomingMessageError(IOError):
    """Error indicating problems with the incoming request"""
    def __init__(self, kind, desc=None, args=None):
        self.kind=kind
        self.desc=desc
        self.err_args=args
        msg="{} ({})".format(kind,desc) if desc else kind
        super().__init__(msg)


class ServerCommThread(controller.QTaskThread):
    """
    Server communication thread controller.

    Setup args:
        - ``socket``: communication socket
        - ``plugin``: :class:`ServerPlugin` instance used to fulfil requests
    """
    def setup_task(self, socket, plugin):
        super().setup_task()
        self.socket=socket
        self.socket.set_timeout(1.)
        self.plugin=plugin
        self.peer_name=socket.get_peer_name()
        self.add_job("check_message",self.check_message,0,initial_call=False)
        self.subscribe_commsync(self.receive_frames,**plugin.get_frame_stream_parameters())
        self.frames_cnt=StreamIDCounter()
        self.frames_accum=FramesAccumulator()
        self.frames_accum_size=0
    def finalize_task(self):
        self.socket.close()
        self.plugin.disconnect()
        return super().finalize_task()

    _key_types={"int":int, "str":py3.textstring, "float":(int,float)}
    def _check_value_type(self, value, dtype):
        if isinstance(dtype,tuple):
            if isinstance(value,(tuple,list)) and len(value)==len(dtype):
                return all(self._check_value_type(v,t) for v,t in zip(value,dtype))
            else:
                return False
        if isinstance(dtype,list):
            if isinstance(value,(tuple,list)):
                return all(self._check_value_type(v,dtype[0]) for v in value)
            else:
                return False
        return isinstance(value,self._key_types[dtype])
    def get_message_key(self, msg, key, branch=None, desc=None, dtype=None):
        """
        Get a certain value in the message dictionary.

        If `branch` and `desc` are specified, they are used to generate error messages.
        `dtype` can specify the expected value type: ``"int"``, ``"float"``, ``"str"``, a tuple, or a list of datatypes.
        """
        full_key="{}/{}".format(branch,key) if branch else key
        branch=" '{}'".format(branch) if branch else ""
        if not dictionary.is_dictionary(msg,generic=True):
            raise IncomingMessageError("wrong_type",desc="Message value{} is not a dictionary".format(branch),args={"branch":branch})
        if key not in msg:
            raise IncomingMessageError("missing_argument",desc=desc or "Missing value '{}'".format(full_key),args={"key":full_key,})
        value=msg[key]
        if dtype is not None and not self._check_value_type(value,dtype):
            raise IncomingMessageError("wrong_type",desc=desc or "Wrong type of value '{}'".format(full_key),args={"key":full_key,"value":value,"dtype":dtype})
        return value
    def _build_error_message(self, error):
        reply=dictionary.Dictionary({"purpose":"error","parameters":{"name":error.kind,"args":error.err_args}})
        if error.desc:
            reply["parameters/description"]=error.desc
        return reply
    def receive_frames(self, src, tag, msg):
        """Receive camera frames and store them in the accumulator"""
        if self.frames_cnt.receive_message(msg):
            self.frames_accum.clear()
        if self.frames_accum_size>0:
            self.frames_accum.add_message(msg)
            self.frames_accum.cut_to_size(self.frames_accum_size,from_end=True)
        else:
            self.frames_accum.clear()

    def send_message(self, msg):
        """Send a new message to the peer"""
        msg=dictionary.as_dict(msg,style="nested")
        payload=None
        if "payload" in msg:
            payload=msg["payload"]
            msg["payload"]={"shape":payload.shape,"dtype":payload.dtype.str,"nbytes":payload.nbytes}
        self.socket.send_fixedlen(json.dumps(msg))
        if payload is not None:
            self.socket.send_fixedlen(payload.tobytes())
    def recv_message(self):
        """Receive a message from the peer"""
        msg=json.loads(net.recv_JSON(self.socket))
        if not isinstance(msg,dict):
            raise IncomingMessageError("wrong_format","Wrong incoming message format",{"value":msg})
        if list(msg)==["protocol"]:
            return msg
        msg=dictionary.Dictionary(msg)
        if "payload" in msg:
            shape=self.get_message_key(msg["payload"],"shape","branch",dtype=["int"])
            dtype=self.get_message_key(msg["payload"],"dtype","branch",dtype="str")
            nbytes=msg.get("payload/nbytes",np.prod(shape)*np.dtype(dtype).itemsize)
            try:
                payload=self.socket.recv_fixedlen(nbytes)
                payload=np.frombuffer(payload,dtype=dtype).reshape(shape)
            except (TypeError,ValueError):
                raise IncomingMessageError("wrong_type","Wrong payload specification",{"value":msg["payload"]})
            except net.SocketTimeout:
                raise IncomingMessageError("wrong_argument","Payload size is smaller than specified",{"value":nbytes})
            msg.add_entry("payload",payload,force=True)
        return msg
    def check_message(self):
        """Check for incoming messages and reply if necessary"""
        try:
            try:
                msg=self.recv_message()
                reply=self.process_message(msg)  # pylint: disable=assignment-from-none
            except IncomingMessageError as error:
                reply=self._build_error_message(error)
            if reply is not None:
                self.send_message(reply)
        except net.SocketTimeout:
            pass
        except net.SocketError:
            self.stop()
    
    def process_message(self, msg):
        """Process the incoming message and generate the reply"""
        if list(msg)==["protocol"]:
            return {"protocol":"1.0"}
        purpose=msg.get("purpose","request")
        mid=msg.get("id",None)
        if purpose=="request":
            name=self.get_message_key(msg,"parameters/name",dtype="str")
            args=msg.get("parameters/args",{})
            if not dictionary.is_dictionary(args,generic=True):
                raise IncomingMessageError("wrong_type","Arguments must be a dictionary",{"value":args})
            kind,rname=name.split("/",maxsplit=1) if name.find("/")>=0 else ("",name)
            if kind=="gui":
                result=self.process_gui_request(rname,args)
            elif kind=="save":
                result=self.process_save_request(rname,args)
            elif kind=="cam":
                result=self.process_cam_request(rname,args)
            elif kind=="stream":
                result=self.process_stream_request(rname,args)
            else:
                raise IncomingMessageError("wrong_request","Unrecognized request '{}'".format(name),{"value":name})
            if not dictionary.is_dictionary(result,generic=True):
                result={"result":result}
            result={"name":name,"args":result}
            if "payload" in result["args"]:
                result["payload"]=result["args"].pop("payload")
        else:
            raise IncomingMessageError("wrong_purpose","Unrecognized purpose '{}'".format(purpose),{"value":purpose})
        if result is not None:
            payload=result.pop("payload",None)
            reply={"purpose":"reply","parameters":result}
            if mid is not None:
                reply["id"]=mid
            if payload is not None:
                reply["payload"]=payload
            return reply
    def _as_dict(self, d, style="flat"):
        if isinstance(d,dictionary.Dictionary):
            return d.as_dict(style=style)
        return d
    def process_gui_request(self, name, args):
        """Process gui-related request"""
        if name in ["get/value","get/indicator"]:
            value_name=args.get("name","")
            try:
                result=self.plugin.gui_control(name,value_name)
            except KeyError:
                raise IncomingMessageError("wrong_argument","Could not find gui {} '{}'".format(name[4:],value_name),{"value":value_name})
            return {"name":value_name,"value":self._as_dict(result)}
        if name in ["set/value","set/indicator"]:
            value_name=self.get_message_key(args,"name",branch="parameters/args")
            value=self.get_message_key(args,"value",branch="parameters/args")
            try:
                result=self.plugin.gui_control(name,value_name,value=value)
            except KeyError:
                raise IncomingMessageError("wrong_argument","Could not find gui {} '{}'".format(name[4:],value_name),{"value":value_name})
            except (ValueError,TypeError):
                raise IncomingMessageError("wrong_type","Wrong type for the supplied value of gui {} '{}'".format(name[4:],value_name),{"value":value})
            return {"name":value_name,"value":self._as_dict(result)}
        raise IncomingMessageError("wrong_request","Unrecognized gui request '{}'".format(name),{"value":name})
    def process_save_request(self, name, args):
        """Process saving-related request"""
        if name=="start":
            try:
                self.plugin.save_control(start=True,params=args)
            except (ValueError,TypeError):
                raise IncomingMessageError("wrong_type","Wrong type for the supplied acquisition parameters",{"value":args})
            return "success"
        if name=="stop":
            self.plugin.save_control(start=False)
            return "success"
        if name=="snap":
            source=args.get("source")
            self.plugin.save_control(mode="snap",start=True,source=source,params=args)
            return "success"
        raise IncomingMessageError("wrong_request","Unrecognized save request '{}'".format(name),{"value":name})
    def process_cam_request(self, name, args):
        """Process camera-related request"""
        if name in ["acq/start","acq/stop"]:
            self.plugin.cam_control(name)
            return "success"
        if name=="param/get":
            try:
                value_name=args.get("name","")
                result=self.plugin.cam_control(name,value=value_name)
                return {"name":value_name,"value":self._as_dict(result)}
            except KeyError:
                raise IncomingMessageError("wrong_argument","Could not find camera parameter '{}'".format(value_name),{"value":value_name})
        if name=="param/set":
            args=dictionary.Dictionary(args).map_self(lambda v: tuple(v) if isinstance(v,list) else v) # JSON turns tuples into lists
            self.plugin.cam_control(name,value=args)
            return "success"
        raise IncomingMessageError("wrong_request","Unrecognized camera request '{}'".format(name),{"value":name})
    def process_stream_request(self, name, args):
        """Process data streaming/acquisition-related request"""
        if name=="buffer/setup":
            if "size" in args:
                self.frames_accum_size=self.get_message_key(args,"size",branch="parameters/args",dtype="int")
            elif self.frames_accum_size==0:
                self.frames_accum_size=1
            if self.frames_accum_size>0:
                self.frames_accum.cut_to_size(self.frames_accum_size,from_end=True)
            else:
                self.frames_accum.clear()
            return self.process_stream_request("buffer/status",{})
        elif name=="buffer/clear":
            self.frames_accum.clear()
            return self.process_stream_request("buffer/status",{})
        elif name=="buffer/status":
            n=self.frames_accum.nframes()
            if n:
                _,fidx,_=self.frames_accum.get_slice(0,1,flatten=True)
                _,lidx,_=self.frames_accum.get_slice(-1,flatten=True)
                return {"filled":n,"size":self.frames_accum_size,"first_index":int(fidx[0]),"last_index":int(lidx[0])}
            else:
                return {"filled":0,"size":self.frames_accum_size,"first_index":0,"last_index":0}
        elif name=="buffer/read":
            if "n" in args:
                nread=self.get_message_key(args,"n",branch="parameters/args",dtype="int")
            else:
                nread=None
            n=self.frames_accum.nframes()
            peek=bool(args.get("peek",False))
            if nread is None:
                frames,indices,_=self.frames_accum.get_slice(0)
                if not peek:
                    self.frames_accum.clear()
            elif nread>=0:
                frames,indices,_=self.frames_accum.get_slice(0,nread)
                if not peek:
                    self.frames_accum.cut_to_size(max(0,n-nread),from_end=True)
            else:
                frames,indices,_=self.frames_accum.get_slice(nread,None)
                if not peek:
                    self.frames_accum.clear()
            if frames:
                if frames[0].ndim==3:
                    payload=np.concatenate(frames)
                    fidx=indices[0][0]
                    lidx=indices[-1][-1]
                else:
                    payload=np.array(frames)
                    fidx=indices[0]
                    lidx=indices[-1]
            else:
                payload=np.zeros((0,0,0),dtype="<u2")
                fidx=lidx=0
            return {"payload":payload,"first_index":int(fidx),"last_index":int(lidx)}
            




class ServerPlugin(base.IPlugin):
    _class_name="server"
    _default_start_order=100
    def setup(self):
        self.setup_gui_sync()
        self.thread_name_gen=general.NamedUIDGenerator()
        self.ctl.add_job("listen",self.listen,0.1,initial_call=False)
        self.port=self.parameters.get("port",18923)
        self.ip=self.parameters.get("ip",net.get_local_addr())
        self.nconn=0
    def setup_gui(self):
        self.table=self.gui.add_plugin_box("server","Server",index=100)
        self.table.add_text_label("ip",label="IP address")
        self.table.add_num_label("nconn",label="Number of connections",formatter=".0f")
    
    @controller.call_in_gui_thread
    def update_gui(self, ip=None, nconn=0):
        if ip is not None:
            self.table.v["ip"]="{}:{}".format(*ip)
        self.nconn+=nconn
        self.table.v["nconn"]=self.nconn
    def listen(self):
        """
        Listen on the port for new connections.

        Block the execution, so no other jobs/commands can be executed.
        """
        max_port=self.port+100
        while self.port<max_port:
            try:
                self.update_gui(ip=(self.ip,self.port))
                net.listen(self.ip,self.port,self.connect,wait_callback=self.ctl.check_messages)
                break
            except OSError:
                self.port+=1
    def connect(self, socket):
        """Mark incoming connection"""
        self.update_gui(nconn=1)
        ServerCommThread(self.thread_name_gen(self.ctl.name+".comm_thread"),kwargs={"socket":socket,"plugin":self}).start()
    def disconnect(self):
        """Mark disconnection"""
        if self._running:
            self.update_gui(nconn=-1)
    
    @controller.call_in_gui_thread(silent=True)
    def gui_control(self, action, name, value=None):
        """Perform GUI control operation"""
        op,kind=action.split("/")
        if op=="set":
            if kind=="value":
                self.gui.main_frame.set_value(name,value)
            else:
                self.gui.main_frame.set_indicator(name,value)
        if kind=="value":
            return self.gui.main_frame.get_value(name)
        return self.gui.main_frame.get_indicator(name)
    def save_control(self, mode="full", start=True, source=None, params=None):
        """Perform save control operation"""
        self.guictl.call_thread_method("toggle_saving",mode,start=start,source=source,change_params=params,no_popup=True)
    def cam_control(self, action, value=None):
        """Perform cam control operation"""
        if action=="acq/start":
            self.extctls["camera"].cs.acq_start()
        if action=="acq/stop":
            self.extctls["camera"].cs.acq_stop()
        if action=="param/get":
            name=value or ""
            return self.extctls["camera"].v["parameters",name]
        if action=="param/set":
            self.extctls["camera"].cs.apply_parameters(value)
    def get_frame_stream_parameters(self):
        """Get parameters required for the subscription to the camera source"""
        return {"srcs":self.extctls["preprocessor"].name,"tags":"frames/new"}