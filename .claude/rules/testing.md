# Testing Rules

- pytest only — never unittest
- Test file names mirror source: `src/flockr/config.py` → `tests/test_config.py`
- Take writing tests as seriously as the code it is testing 
- Integration tests fully bootstrap the app before testing it — no partial mocks\
- Martin Fowler's test pyramid 
- Use descriptive test names: `test_returns_404_when_user_does_not_exist`
- Test config lives in `tests/` or `src/test/resources/` — never in source tree
- Martin Fowler pyramid: unit → integration → e2e (most tests at unit level) for raw speed
- Limited number of comprehensive e2e integration tets.  No flocks in these. 
- Don't allow ur tests to fail due to the OS not resoures includinug ports being locked.  
- Spin up random ports, handle and rlease them using appropriate language constructions
- Either bootstrap ur own externals or spin up docker
- 
d 