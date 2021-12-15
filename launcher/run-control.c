#pragma comment(linker, "/SUBSYSTEM:windows /ENTRY:mainCRTStartup")

#include <windows.h>
#include <stdio.h>

#define CLLEN 4096


int main(int argc, char *argv[]) {
    char call_argv[CLLEN];
    strcpy_s(call_argv,CLLEN,"python\\python.exe cam-control\\control.py");
    for (int i=1;i<argc;i++) {
        strcat_s(call_argv,CLLEN," ");
        strcat_s(call_argv,CLLEN,argv[i]);
    }

    STARTUPINFO si;
    PROCESS_INFORMATION pi;
    memset(&si,0,sizeof(si));
    si.cb=sizeof(si);
    memset(&pi,0,sizeof(pi));
    
    CreateProcess(NULL,call_argv,NULL,NULL,FALSE,0,NULL,NULL,&si,&pi);
    return 0;
}