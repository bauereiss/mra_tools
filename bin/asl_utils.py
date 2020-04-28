#!/usr/bin/env python3

# add one level of indentation to code
def indent(code):
    return [ "    " + l for l in code ]

# remove one level of indentation from code
def unindent(code):
    cs = []
    for l in code:
        if l != "" and l[0:4] != "    ":
            print("Malformed conditional code '" + l[0:4] +"'")
            assert False
        cs.append(l[4:])
    return cs

# Execute ASL code often has a header like this:
#
#     if ConditionPassed() then
#         EncodingSpecificOperations();
#
# that we need to transform into a more usable form.
# Other patterns found are:
# - declaring an enumeration before the instruction
# - inserting another line of code between the first and second lines.
#   eg "if PSTATE.EL == EL2 then UNPREDICTABLE;"
# - wrapping the entire instruction in
#    "if code[0].startswith("if CurrentInstrSet() == InstrSet_A32 then"):
#
# Return value consists of (top, cond, dec, exec):
# - additional top level declarations (of enumerations)
# - boolean: is the instruction conditional?
# - additional decode logic (to be added to start of decode ASL)
# - demangled execute logic
def demangleExecuteASL(code):
    tops = None
    conditional = False
    decode = None
    if code[0].startswith("enumeration ") and code[1] == "":
        tops = code[0]
        code = code[2:]
    if code[0].startswith("if CurrentInstrSet() == InstrSet_A32 then"):
        first = code[0]
        code = code[1:]
        mid = code.index("else")
        code1 = unindent(code[:mid])
        code2= unindent(code[mid+1:])
        (tops1, conditional1, decode1, code1) = demangleExecuteASL(code1)
        (tops2, conditional2, decode2, code2) = demangleExecuteASL(code2)
        assert tops1 == None and tops2 == None
        assert conditional1 == conditional2
        code = [first] + indent(code1) + ["else"] + indent(code2)
        ([], conditional1, "\n".join([decode1 or "", decode2 or ""]), code)

    if code[0] == "if ConditionPassed() then":
        conditional = True
        code = code[1:] # delete first line
        code = unindent(code)
    if code[0] == "bits(128) result;":
        tmp = code[0]
        code[0] = code[1]
        code[1] = tmp
    elif len(code) >= 2 and code[1] == "EncodingSpecificOperations();":
        decode = code[0]
        code = code[1:]
    if code[0].startswith("EncodingSpecificOperations();"):
        rest = code[0][29:].strip()
        if rest == "":
            code = code[1:]
        else:
            code[0] = rest
    return (tops, conditional, decode, code)

