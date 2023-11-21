from setuptools import setup

setup(
    name="metricq_source_sysinfo",
    version="1.0",
    author="TU Dresden",
    python_requires=">=3.10",
    packages=["metricq_source_sysinfo"],
    scripts=[],
    entry_points="""
      [console_scripts]
      metricq-source-sysinfo=metricq_source_sysinfo:run
      """,
    install_requires=[
        "click",
        "click_log",
        "metricq ~= 5.3",
        "psutil",
    ],
    use_scm_version=True,
)
