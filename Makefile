.PHONY: verify verify-repeat protection-audit

verify:
	python3 conformance/verify_conformance.py

verify-repeat:
	python3 conformance/verify_conformance.py > /tmp/aaa_verify_run1.txt
	python3 conformance/verify_conformance.py > /tmp/aaa_verify_run2.txt
	diff -u /tmp/aaa_verify_run1.txt /tmp/aaa_verify_run2.txt

protection-audit:
	./scripts/audit_branch_protection.sh main
