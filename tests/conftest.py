"""Pytest configuration for automatic fixture discovery across dependent packages.

Registers every fixture module in this package's fixtures package, and in the
equivalent fixtures package of every installed package that depends on this
package, as a pytest plugin. This makes all discovered fixtures available in
every test module without explicit imports.
"""

pytest_plugins = ["pyrig_fixtures.rig.tests.conftest"]
