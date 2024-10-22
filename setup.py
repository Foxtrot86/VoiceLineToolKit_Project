from cx_Freeze import setup, Executable

# ADD FILES
files = ['icon.ico', 'config.ini', 'logs.txt']

# TARGET
target = Executable(
    script='VoiceLineToolKit.py',
    base='Win32GUI',
    icon='icon.ico'
)

# SETUP CX FREEZE
setup(
    name='VoiceLineToolKit',
    version='1.4',
    description='VoiceLineToolKit aim to encourage you to seamlessly integrate your own voices into Ready or Not. \n'
                'This tool automates the most tedious parts of the dubbing process—file naming, audio splitting, '
                'enhancement, and game implementation—allowing you to focus entirely on what matters most: '
                'the best performance for your voice lines.',
    author='Foxtrot',
    options={'build_exe': {'include_files': files}},
    executables=[target]
)