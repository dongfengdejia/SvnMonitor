#!/usr/bin/python


import sys
import os
import ConfigParser
import time
import subprocess
import pprint

componentRange = ["MOAM", "SWM", "REM", "DEM", "MCTRL", "URI", "FRI", "SYSADAPT"]

inputMap = {"userName"       : None,
            "passWord"       : None,
            "component"      : None,
            "worksapce"      : None,
            "svnUrl"         : None,
            "commitMessage"  : None,
            "lockStatus"     : None,
            "logger"         : None
}

def getCommitMessage(iniFile):
    iniContent = open(iniFile, "r").read()
    inputMap["commitMessage"] = iniContent.strip().split("commitMessage = '''")[1].strip("'")
    
def getIniInfo(iniFile):
    if os.path.exists(iniFile):
        iniParse = ConfigParser.ConfigParser()
        iniParse.read(iniFile)
        inputMap["component"] = iniParse.get("basicConf", "component")
        inputMap["workspace"] = iniParse.get("basicConf", "workspace")
        inputMap["svnUrl"] = iniParse.get("basicConf", "svnUrl")
        inputMap["userName"] = iniParse.get("basicConf", "userName&passWord").split(":")[0].strip()
        inputMap["passWord"] = iniParse.get("basicConf", "userName&passWord").split(":")[1].strip()
        getCommitMessage(iniFile)
    else:
        print ">>> Can't find the input file: ", iniFile
        sys.exit(-1)

def checkInput():
    if ((inputMap["component"] not in componentRange) or 
        inputMap["userName"] == None or inputMap["passWord"] == None or
        inputMap["workspace"] == None or inputMap["svnUrl"] == None or
        (inputMap["component"].upper() not in inputMap["svnUrl"]) or
        ("PRODUCT" not in inputMap["commitMessage"]) or
        ("COMPLETED" not in inputMap["commitMessage"]) or
        ("DESCRIPTION" not in inputMap["commitMessage"]) or
        ("TESTED" not in inputMap["commitMessage"])):
        return False
    else:
        loggerFile = os.path.join(inputMap["workspace"], "svnAutoCommit.log")
        inputMap["logger"] = open(loggerFile,"w")
        inputMap["logger"].write("### Start automatic commit code ###")
        inputMap["logger"].write("\r\n")
        return True

def getLockStatus():
    lockFile = inputMap["svnUrl"].rstrip("trunk/") + "/LOCKS/locks.conf"
    lockStatus = "locked"
    inputMap["logger"].write("lockFile: " + lockFile + "\r\n")
    pattern = "#trunk/.* = *()"
    command = "svn --username %s --password %s --non-interactive cat %s" % (inputMap["userName"],inputMap["passWord"],lockFile)
    inputMap["logger"].write("check lock status command: " + command + "\r\n")
    pro = subprocess.Popen(command, stdout = subprocess.PIPE, stderr=subprocess.PIPE)
    if pattern in pro.stdout.read():
        lockStatus = "unlock"
    inputMap["lockStatus"] = lockStatus
    
def workspaceRebase():
    rebaseStatus = True
    command = "svn update --username %s --password %s --non-interactive %s" % (inputMap["userName"],inputMap["passWord"],inputMap["workspace"])
    inputMap["logger"].write("rebase workspace command: " + command + "\r\n")
    
    pro = subprocess.Popen(command, stdout = subprocess.PIPE, stderr=subprocess.PIPE)
    
    if pro.stderr and pro.stderr.read():
        print ">>> Rebase code failure: ", pro.stderr.read()
        inputMap["logger"].write(">>> Rebase code failure: %s \r\n" % pro.stderr.read())
        return False

    output = pro.stdout.readlines()
    if output:
        inputMap["logger"].write(">>> Rebase code: %s \r\n" % output)
    else:
        inputMap["logger"].write(">>> Rebase code not have output print\r\n")
        return False
        
    for line in output:
        if line.startswith("C    "):
            rebaseStatus = False
            print ">>> Rebase conflict: ", line
            inputMap["logger"].write(">>> Rebase conflict: %s \r\n" % line)
        elif "At revision" in line:
            print ">>> Rebase to the version: ", line
            inputMap["logger"].write(">>> Rebase to the version: %s \r\n" % line)
        elif "Summary of conflicts" in line or "Text conflicts" in line:
            rebaseStatus = False
            print ">>> Rebase conflict: ", line
            inputMap["logger"].write(">>> Rebase conflict: %s \r\n" % line)
    return rebaseStatus
    
def workspaceCommit():
    commitStatus = False
    commitMessage = os.path.join(inputMap["workspace"],"commitMessage.txt")
    commitMessageFile = open(commitMessage,"w")
    commitMessageFile.write(inputMap["commitMessage"])
    command = "svn commit --username %s --password %s --non-interactive %s -F \"%s\"" % \
        (inputMap["userName"],inputMap["passWord"],inputMap["workspace"],commitMessage)
    inputMap["logger"].write("commit workspace command: " + command + "\r\n")
    
    pro = subprocess.Popen(command, stdout = subprocess.PIPE, stderr=subprocess.PIPE)
    if pro.stderr and pro.stderr.read():
        print ">>> Commit code failure: ", pro.stderr.read()
        inputMap["logger"].write(">>> Commit code failure: %s \r\n" % pro.stderr.read())
        return False
        
    output = pro.stdout.readlines()
    if output:
        inputMap["logger"].write(">>> Commit code: %s \r\n" % output)
    else:
        inputMap["logger"].write(">>> Commit code not have output print\r\n")
        return False
    for line in output:
        if "Commit failed" in line or "Aborting commit" in line:
            commitStatus = False
            print ">>> Commit failure: ", line
            inputMap["logger"].write(">>> Commit failure: %s \r\n" % line)
        elif "Committed revision" in line:
            commitStatus = True
            print ">>> Commit pass: ", line
            inputMap["logger"].write(">>> Commit pass: %s \r\n" % line)
    return commitStatus

def myExit(exitCode):
    inputMap["logger"].write("inputMap: " + str(inputMap))
    inputMap["logger"].write("\r\n")
    inputMap["logger"].write("### End of automatic commit code ###")
    sys.exit(exitCode)
    
if __name__ == "__main__":
    
    if len(sys.argv) == 1:
        getIniInfo(os.path.join(os.getcwd(), "svnAutoCommit.ini"))
    else:
        getIniInfo(sys.argv[1])
        
    if not checkInput():
        print ">>> The input info not right: "
        pprint.pprint(inputMap)
        sys.exit(-1)
    else:
        inputMap["logger"].write("inputMap: " + str(inputMap))
        inputMap["logger"].write("\r\n")
    
    counter = 1
    while 1:
        getLockStatus()
        if inputMap["lockStatus"] == "unlock":
            if workspaceRebase() and workspaceCommit():
                print ">>> %s commit to %s pass" % (inputMap["workspace"],inputMap["svnUrl"])
                inputMap["logger"].write(">>> %s commit to %s pass\r\n" % (inputMap["workspace"],inputMap["svnUrl"]))
                myExit(0)
            else:
                print ">>> %s commit to %s failure" % (inputMap["workspace"],inputMap["svnUrl"])
                inputMap["logger"].write(">>> %s commit to %s failure\r\n" % (inputMap["workspace"],inputMap["svnUrl"]))
                myExit(-1)
        print ">>> %d : %s still locked, waitting 300s" % (counter, inputMap["component"])
        inputMap["logger"].write(">>> %d : %s still locked, waitting 300s\r\n" % (counter, inputMap["component"]))
        counter += 1
        time.sleep(300)