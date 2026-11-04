"""Minimum environment for bundled collectors and model processes."""
import os,sys

ALLOWED={'SYSTEMROOT','WINDIR','PATH','PATHEXT','TEMP','TMP','USERPROFILE','LOCALAPPDATA','APPDATA','PROGRAMFILES','PROGRAMFILES(X86)','PROGRAMDATA','COMSPEC','HOMEDRIVE','HOMEPATH','NUMBER_OF_PROCESSORS','PROCESSOR_ARCHITECTURE','PROCESSOR_IDENTIFIER','OS','ALLUSERSPROFILE','PUBLIC','USERNAME','USERDOMAIN','LANG','LC_ALL','TZ'}
def environment(extra=None,same_bundle=False):
    result={k:v for k,v in os.environ.items() if k.upper() in ALLOWED}
    if same_bundle and getattr(sys,'frozen',False):
        result.update({k:v for k,v in os.environ.items() if k in ('_PYI_APPLICATION_HOME_DIR','_PYI_PARENT_PROCESS_LEVEL','_PYI_ARCHIVE_FILE','_PYI_SPLASH_IPC')})
    result.update(extra or {})
    return result
