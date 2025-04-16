SHELL := /bin/bash
.SHELLFLAGS := -ec

PROJECT := "mcp-redmine" # overloads as binary name, too
PACKAGE := "mcp_redmine"
VERSION := $(shell date +%Y.%m.%d.%H%M%S)

version-bump:
	sed -i "s/mcp-redmine==[0-9.]*\"/mcp-redmine==$(VERSION)\"/g" README.md
	sed -i "s/version = \"[^\"]*\"/version = \"$(VERSION)\"/" pyproject.toml
	sed -i "s/VERSION = \"[^\"]*\"/VERSION = \"$(VERSION)\"/" $(PACKAGE)/server.py

version-bump-claude-desktop:
	sed -i "s/mcp-redmine==[0-9.]*\"/mcp-redmine==$(VERSION)\"/g" ~/.config/Claude/claude_desktop_config.json

publish-test:
	rm -rf dist/*
	$(MAKE) version-bump
	uv build
	uv publish --token "$$PYPI_TOKEN_TEST" --publish-url https://test.pypi.org/legacy/
	git checkout README.md pyproject.toml $(PACKAGE)/server.py

publish-prod:
	rm -rf dist/*
	$(MAKE) version-bump
	$(MAKE) version-bump-claude-desktop
	uv build
	uv lock
	uv publish --token "$$PYPI_TOKEN_PROD"
	git commit -am "Published version $(VERSION) to PyPI"
	git push

package-inspect-test:
	rm -rf /tmp/test-mcp-redmine
	uv venv /tmp/test-mcp-redmine --python 3.12
	source /tmp/test-mcp-redmine/bin/activate && uv pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ mcp-redmine
	tree /tmp/test-mcp-redmine/lib/python3.12/site-packages/$(PACKAGE)
	source /tmp/test-mcp-redmine/bin/activate && which $(PROJECT)

package-inspect-prod:
	rm -rf /tmp/test-mcp-redmine
	uv venv /tmp/test-mcp-redmine --python 3.12
	source /tmp/test-mcp-redmine/bin/activate && uv pip install mcp-redmine
	tree /tmp/test-mcp-redmine/lib/python3.12/site-packages/$(PACKAGE)
	source /tmp/test-mcp-redmine/bin/activate && which $(PROJECT)

package-run-test:
	uvx --default-index https://test.pypi.org/simple/ --index https://pypi.org/simple/ --from mcp-redmine mcp-redmine

package-run-prod:
	uvx --from mcp-redmine mcp-redmine