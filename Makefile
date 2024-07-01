SHELL := /bin/bash
PYTHON := python    # parent project can override setup python
CLEAN := pywub.egg-info dist
PHONY =

help:
	@echo valid Make targets:
	@# https://stackoverflow.com/questions/4219255/how-do-you-get-the-list-of-targets-in-a-makefile
	@LC_ALL=C $(MAKE) -pRrq -f $(firstword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/(^|\n)# Files(\n|$$)/,/(^|\n)# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | egrep -v -e '^[^[:alnum:]]' -e '^$@$$'
PHONY += help


# Must not be first target
clean:
	$(RM) -r $(CLEAN)
PHONY += clean


.PHONY: $(PHONY)
