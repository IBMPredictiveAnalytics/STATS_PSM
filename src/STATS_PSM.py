# STATS PSM extension command
# This replaces the PSM dialog box interface to FUZZZY with a full extension command.


__author__ = "JKP"
__version__ = "1.0.0"

# history
# 16-jul-2022 original version

import spss, spssaux, random, sys
from extension import Template, Syntax, processcmd


# debugging
        # makes debug apply only to the current thread
#try:
    #import wingdbstub
    #import threading
    #wingdbstub.Ensure()
    #wingdbstub.debugger.SetDebugThreads({threading.get_ident(): 1})
#except:
    #pass

def Run(args):
    """Run the STATS PSM command"""
    
    args = args[list(args.keys())[0]]
    
    oobj = Syntax([
    Template("GROUP", subc="", var="group", ktype="existingvarlist", islist=False),
    Template("BY", subc="", var="by", ktype="existingvarlist", islist=True),
    Template("PROPENSITY", subc="", var="propensity", ktype="varname", islist=False),
    Template("FUZZ", subc="", var="fuzz", ktype="float", islist=False),
    Template("NEWDEMANDERIDVAR", subc="", var="matchidvar", ktype="varname", islist=False),
    Template("SUPPLIERID", subc="", var="id", ktype="existingvarlist",  islist=False),  
    Template("OUTPUTDS", subc="", ktype="varname", var="outputds", islist=False),
    Template("USEDCONTROLSDS", subc="", ktype="varname", var="usedcontrolsds", islist=False),
    
    Template("DRAWPOOLSIZE", subc="OPTIONS", var="drawpool", ktype="varname"),
    Template("SAMPLEWITHREPLACEMENT", subc="OPTIONS", var="samplewithreplacement", ktype="bool"),
    Template("EXACTPRIORITY", subc="OPTIONS", var="exactpriority", ktype="bool"),
    Template("MINIMIZEMEMORY", subc="OPTIONS", var="minimizememory",  ktype="bool"),
    Template("SHUFFLE", subc="OPTIONS", var="shuffle", ktype="bool"),
    Template("SEED", subc="OPTIONS", var="seed", ktype="int",vallist=(-2**31+1, 2**31-1))
    ])

    #enable localization
    global _
    try:
        _("---")
    except:
        def _(msg):
            return msg

    if "HELP" in args:
        #print helptext
        helper()
    else:
        processcmd(oobj, args, psm, vardict=spssaux.VariableDict())

###Template("MATCHGROUPVAR", subc="", var="hashvar", ktype="varname"),   #??

def psm(group, by, propensity, fuzz, id, matchidvar, outputds, usedcontrolsds=None,
    drawpool=None, samplewithreplacement=False, exactpriority=False,
    minimizememory=False, shuffle=False, seed=None):
    """PSM command implementation"""

    ds = spss.ActiveDataset()
    if ds == "*":
        ds = "D" + str(random.uniform(.05, 1.))
        spss.Submit("DATASET NAME " + ds)
        
    matchgroup = "M" + str(random.uniform(.05, 1.))
    tempdsname = "D" + str(random.uniform(.05, 1.))

    lrcmd = rf"""LOGISTIC REGRESSION 
    {makevarlist(group, by)}
    /SAVE=PRED({propensity})."""
    
    # Run the logistic regression command wrapped in OMS commands to suppress
    # undesired output.
    tag1 = "T" + str(random.uniform(.05,1))
    tag2 = "T" + str(random.uniform(.05,1))
    oms = f"""oms select tables /if subtypes=["Variables not in the Equation" 'Variables in the Equation']
    /destination viewer=NO
    /tag = '{tag1}'.
oms select tables /if subtypes=['Variables in the Equation'] instances=[LAST]
    /destination viewer=yes
    /tag = '{tag2}'."""
    spss.Submit(oms)
    try:
        spss.Submit(lrcmd)
    except:
        raise ValueError("Logistic Regression step failed")
    finally:
        spss.Submit(f"""omsend tag=['{tag1}' '{tag2}'].""")

    if seed is None:
        seedcode = ""
    else:
        seedcode = f"SEED={seed}"
    # Run the FUZZY command using the output from LOGISTIC REGRESSION
    fuzzycmd = rf"""FUZZY BY={propensity} SUPPLIERID={id} NEWDEMANDERIDVARS={matchidvar} 
    GROUP={group} EXACTPRIORITY={exactpriority}
    FUZZ={fuzz} DS3={tempdsname} MATCHGROUPVAR={matchgroup}
    /OPTIONS SAMPLEWITHREPLACEMENT={samplewithreplacement} MINIMIZEMEMORY={minimizememory} SHUFFLE={shuffle} {seedcode}."""
    try:
        spss.Submit(fuzzycmd)
    except:
        raise ValueError(_("""Matching command failed.  If FUZZY is not installed, add it via Extensions > Extension Hub."""))
    
    # cleanup
    
    spss.Submit(f"""
    DATASET ACTIVATE {ds}.
    DELETE VARIABLES {matchgroup}.
    DATASET COPY {outputds}.
    DATASET ACTIVATE {outputds}.
    SELECT IF {group} EQ 1.
    DATASET ACTIVATE {tempdsname}.
    DELETE VARIABLES {matchgroup}.
    DATASET ACTIVATE {outputds}.
    ADD FILES /FILE=* /FILE={tempdsname}.
    EXECUTE.""")

    if usedcontrolsds is None:
        spss.Submit(f"""DATASET CLOSE {tempdsname}.""")
    else:
        spss.Submit(f"""DATASET ACTIVATE {tempdsname}.
        DATASET NAME {usedcontrolsds}.
        DATASET ACTIVATE {ds}.""")
    

def makevarlist(group, by):
    """return variable list syntax according to measurement levels"""
        
    catvars = spssaux.VariableDict(by, variableLevel=["nominal", "ordinal"]).variables
    syntax = f"""VARIABLES {group} WITH {" ".join(by)}"""
    if catvars:
        syntax = syntax + "\n/CATEGORICAL " + " ".join(catvars)
    return syntax

    
def helper():
    """open html help in default browser window
    
    The location is computed from the current module name"""

    import webbrowser, os.path

    path = os.path.splitext(__file__)[0]
    helpspec = "file://" + path + os.path.sep + \
         "markdown.html"

    # webbrowser.open seems not to work well
    browser = webbrowser.get()
    if not browser.open_new(helpspec):
        print(("Help file not found:" + helpspec))
try:    #override
    from extension import helper
except:
    pass