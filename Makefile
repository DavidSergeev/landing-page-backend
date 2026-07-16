.PHONY: build-ChatFunction

# Custom SAM build step (see template.yaml Metadata.BuildMethod: makefile).
# The default Python build workflow doesn't reliably preserve the Unix
# executable bit on run.sh, which the Lambda Web Adapter execs directly —
# so we control the artifact copy explicitly and chmod it ourselves.
build-ChatFunction:
	pip install --target "$(ARTIFACTS_DIR)" -r requirements.txt
	cp -r src "$(ARTIFACTS_DIR)/"
	cp run.sh "$(ARTIFACTS_DIR)/"
	chmod 755 "$(ARTIFACTS_DIR)/run.sh"
