SHELL := /bin/bash
.SHELLFLAGS := -ec

.PHONY: publish-test publish-prod package-inspect-test package-inspect-prod package-run-test package-run-prod

VERSION := $(shell date +%Y.%m.%d.%H%M%S)

publish-test:
	rm -rf dist/*
	sed -i "s/version = \"[^\"]*\"/version = \"$(VERSION)\"/" pyproject.toml
	sed -i "s/mcp-redmine==[0-9.]*\"/mcp-redmine==$(VERSION)\"/g" README.md
	uv build
	uv publish --token "$$PYPI_TOKEN_TEST" --publish-url https://test.pypi.org/legacy/
	git checkout README.md pyproject.toml

publish-prod:
	rm -rf dist/*
	echo "$(VERSION)" > VERSION.txt
	sed -i "s/version = \"[^\"]*\"/version = \"$(VERSION)\"/" pyproject.toml
	sed -i "s/mcp-redmine==[0-9.]*\"/mcp-redmine==$(VERSION)\"/g" README.md
	uv build
	uv publish --token "$$PYPI_TOKEN_PROD"
	git commit -am "Published version $(VERSION) to PyPI"
	git push

package-inspect-test:
	rm -rf /tmp/test-mcp-redmine
	uv venv /tmp/test-mcp-redmine --python 3.13
	source /tmp/test-mcp-redmine/bin/activate && uv pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ mcp-redmine
	tree /tmp/test-mcp-redmine/lib/python3.13/site-packages/mcp_redmine
	source /tmp/test-mcp-redmine/bin/activate && which mcp-redmine

package-inspect-prod:
	rm -rf /tmp/test-mcp-redmine
	uv venv /tmp/test-mcp-redmine --python 3.13
	source /tmp/test-mcp-redmine/bin/activate && uv pip install mcp-redmine
	tree /tmp/test-mcp-redmine/lib/python3.13/site-packages/mcp_redmine
	source /tmp/test-mcp-redmine/bin/activate && which mcp-redmine

package-run-test:
	uvx --default-index https://test.pypi.org/simple/ --index https://pypi.org/simple/ --from mcp-redmine mcp-redmine

package-run-prod:
	uvx --from mcp-redmine mcp-redmine
