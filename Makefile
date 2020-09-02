.PHONY: default
default: all

VERSION = v86A-2020-03
XMLDIR  = v8.6

A64    = ${XMLDIR}/ISA_A64_xml_${VERSION}
A32    = ${XMLDIR}/ISA_AArch32_xml_${VERSION}
SYSREG = ${XMLDIR}/SysReg_xml_${VERSION}


FILTER =
# FILTER = --filter=usermode.json

ASLI = asli
ASL2SAIL = asl2sail
SAIL = sail

arch/regs.asl: ${SYSREG}
	mkdir -p arch
	bin/reg2asl.py $< -o $@

arch/arch.asl arch/arch.tag arch/arch_instrs.asl arch/arch_decode.asl: ${A32} ${A64}
	mkdir -p arch
	bin/instrs2asl.py --altslicesyntax --demangle --verbose -oarch/arch $^ ${FILTER}
	patch -Np0 < arch.patch

ASL += arch/regs.asl
ASL += types.asl
ASL += arch/arch.asl
ASL += support/barriers.asl
ASL += support/hints.asl
ASL += support/debug.asl
ASL += support/feature.asl
ASL += support/interrupts.asl
ASL += support/memory.asl
ASL += support/fetchdecode.asl
ASL += support/stubs.asl
ASL += support/usermode.asl
ASL += arch/arch_instrs.asl
ASL += arch/arch_decode.asl

SAILS = sail/prelude.sail
SAILS += $(addprefix sail/,$(addsuffix .sail,$(basename $(notdir $(ASL)))))
SAILS += sail/epilogue.sail

all :: arch/regs.asl
all :: arch/arch.asl

clean ::
	$(RM) -r arch

# Assumes that patched/* contains a manually fixed version of arch/*
arch.patch ::
	diff -Naur arch patched

asli:
	$(ASLI) $(ASL)

ASL2SAIL_FLAGS = -outdir sail -patches sail/patches -overrides sail/patches/overrides -osails
MONO_FLAGS = -mono_vl
SAIL_FLAGS = -verbose 1 -memo_z3 -no_effects -non_lexical_flow -no_warn
LEM_FLAGS = -undefined_gen -mono_rewrites -auto_mono -lem_mwords -dall_split_errors -dmono_continue
MUTREC_FLAGS = -const_prop_mutrec AArch64_TakeException -const_prop_mutrec AArch32_SecondStageTranslate -const_prop_mutrec AArch64_SecondStageTranslate

gen_sail: $(ASL)
	$(ASL2SAIL) $(ASL2SAIL_FLAGS) $(MONO_FLAGS) $(ASL)

check_sail: $(SAILS)
	$(SAIL) $(SAIL_FLAGS) $(SAILS)

lem: $(SAILS)
	cd sail; $(SAIL) -lem -lem_lib Prelude -o armv86a $(SAIL_FLAGS) $(LEM_FLAGS) $(MUTREC_FLAGS) $(notdir $(SAILS))
# End
