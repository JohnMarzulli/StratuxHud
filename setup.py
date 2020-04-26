from setuptools import setup

installs = ['pytest',
            'pygame',
            'ws4py',
            'requests',
            'bluepy']


setup(
    name='StratuxHud',
    version='1.8.0',
    python_requires='>=3.8',
    description='Graphics for a Heads Up Display projector powered by a Stratux receiver.',
    url='https://github.com/JohnMarzulli/StratuxHud',
    author='John Marzulli',
    author_email='john.marzulli@hotmail.com',
    license='GPL V3',
    install_requires=installs)
