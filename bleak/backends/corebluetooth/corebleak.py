import os
import objc

THIS_FILE = os.path.realpath(__file__)
DIR_PATH = os.path.dirname(THIS_FILE)
FRAMEWORK_PATH = os.path.join(DIR_PATH, "corebleak.framework")

__bundle__ = objc.initFrameworkWrapper("corebleak.framework", 
        frameworkIdentifier="com.kcdvs.corebleak", 
        frameworkPath=objc.pathForFramework(FRAMEWORK_PATH), 
        globals = globals())
