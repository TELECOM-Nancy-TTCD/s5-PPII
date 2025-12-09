VERSION_FILE = VERSION

# Fonction commune pour committer
define commit_version
	@git add $(VERSION_FILE) 
	@git add .
	@git commit -m "Version $$(cat $(VERSION_FILE))"
endef

patch:
	@current=$$(cat $(VERSION_FILE)); \
	major=$$(echo $$current | awk -F. '{print $$1}'); \
	minor=$$(echo $$current | awk -F. '{print $$2}'); \
	patch=$$(echo $$current | awk -F. '{print $$3}'); \
	patch=$$((patch + 1)); \
	new="$$major.$$minor.$$patch"; \
	echo $$new > $(VERSION_FILE); \
	echo "→ Nouvelle version patch : $$new"
	$(call commit_version)

minor:
	@current=$$(cat $(VERSION_FILE)); \
	major=$$(echo $$current | awk -F. '{print $$1}'); \
	minor=$$(echo $$current | awk -F. '{print $$2}'); \
	minor=$$((minor + 1)); \
	new="$$major.$$minor.0"; \
	echo $$new > $(VERSION_FILE); \
	echo "→ Nouvelle version minor : $$new"
	$(call commit_version)

major:
	@current=$$(cat $(VERSION_FILE)); \
	major=$$(echo $$current | awk -F. '{print $$1}'); \
	major=$$((major + 1)); \
	new="$$major.0.0"; \
	echo $$new > $(VERSION_FILE); \
	echo "→ Nouvelle version major : $$new"
	$(call commit_version)


lance:
	. venv/bin/activate && python3 app.py
	@echo "Ouvrir l'url : http://127.0.0.1:5000/""




