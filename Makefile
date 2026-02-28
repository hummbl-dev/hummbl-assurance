.PHONY: verify verify-repeat cli-smoke feature-gate feature-gate-live protection-audit release-check release-receipt cut-release

verify:
	python3 conformance/verify_conformance.py

verify-repeat:
	python3 conformance/verify_conformance.py > /tmp/aaa_verify_run1.txt
	python3 conformance/verify_conformance.py > /tmp/aaa_verify_run2.txt
	diff -u /tmp/aaa_verify_run1.txt /tmp/aaa_verify_run2.txt

cli-smoke:
	./eal verify-receipt --help >/dev/null
	./eal revalidate --help >/dev/null
	./eal compat --help >/dev/null

feature-gate:
	python3 conformance/verify_feature_gate.py

feature-gate-live:
	python3 conformance/verify_feature_gate.py --live-check --require-codex

protection-audit:
	./scripts/audit_branch_protection.sh main

release-check:
	$(MAKE) verify
	$(MAKE) verify-repeat
	$(MAKE) feature-gate
	$(MAKE) protection-audit

release-receipt:
	@test -n "$(TAG)" || (echo "Usage: make release-receipt TAG=vX.Y.Z" >&2; exit 1)
	./scripts/verify_release_receipt.sh "$(TAG)"

cut-release:
	@test -n "$(VERSION)" || (echo "Usage: make cut-release VERSION=vX.Y.Z" >&2; exit 1)
	./scripts/cut_release.sh "$(VERSION)"
