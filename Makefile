.PHONY: build-ChatFunction

# Custom SAM build step (see template.yaml Metadata.BuildMethod: makefile).
# The default Python build workflow doesn't reliably preserve the Unix
# executable bit on run.sh, which the Lambda Web Adapter execs directly —
# so we control the artifact copy explicitly and chmod it ourselves.
build-ChatFunction:
	pip install --target "$(ARTIFACTS_DIR)" -r requirements.txt
	cp -r src "$(ARTIFACTS_DIR)/"
	cp run.sh "$(ARTIFACTS_DIR)/"
	# Strip any CRLF line endings (e.g. introduced by a Windows checkout/editor)
	# so the "#!/bin/bash" shebang stays valid — otherwise the Lambda Web
	# Adapter's exec of run.sh fails with "cannot execute: required file not found".
	sed -i.bak 's/\r$$//' "$(ARTIFACTS_DIR)/run.sh" && rm -f "$(ARTIFACTS_DIR)/run.sh.bak"
	chmod 755 "$(ARTIFACTS_DIR)/run.sh"
