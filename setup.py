from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

setup(
	name="mrp_shortage_report",
	version="0.0.1",
	description="MRP Shortage Report",
	author="Nexgen ERP Technologies",
	author_email="info@nexgenerptechnologies.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
