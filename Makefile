.PHONY: verify verify-repeat cli-smoke protection-audit release-check cut-release

verify:
	python3 conformance/verify_conformance.py

verify-repeat:
	python3 conformance/verify_conformance.py > /tmp/aaa_verify_run1.txt
	python3 conformance/verify_conformance.py > /tmp/aaa_verify_run2.txt
	diff -u /tmp/aaa_verify_run1.txt /tmp/aaa_verify_run2.txt

cli-smoke:
	./eal verify-receipt --help >/dev/null
	./eal compat --help >/dev/null

protection-audit:
	./scripts/audit_branch_protection.sh main

release-check:
	$(MAKE) verify
	$(MAKE) verify-repeat
	$(MAKE) protection-audit

cut-release:
	@test -n "$(VERSION)" || (echo "Usage: make cut-release VERSION=vX.Y.Z" >&2; exit 1)
	./scripts/cut_release.sh "$(VERSION)"
