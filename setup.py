from setuptools import setup

setup(
    name="metricq_source_sysinfo",
    version="0.1",
    author="TU Dresden",
    python_requires=">=3.6",
    packages=["metricq_source_sysinfo"],
    scripts=[],
    entry_points="""
      [console_scripts]
      metricq-source-sysinfo=metricq_source_sysinfo:run
      """,
    install_requires=[
        "click",
        "click-completion",
        "click_log",
        "metricq ~= 2.0",
        "psutil",
    ],
    use_scm_version=True,
)
