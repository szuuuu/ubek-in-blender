import bpy,os,sys

##### getting access 'to ubek.py' #####

UBEK_PY = '' # <-- ENTER THE PATH HERE HERE

if UBEK_PY == '': # for convenience, this should automatically work when 'test.py' is run from the blender text editor
    UBEK_PY = os.path.dirname(bpy.context.space_data.text.filepath)
    
if UBEK_PY == '':
    raise Exception("ENTER THE FULL PATH OF THE 'blender_py' DIRECTORY IN YOUR LOCAL COPY OF 'ubek-in-blender'")
    
if not UBEK_PY in sys.path:
    sys.path.append(UBEK_PY)
    
import ubek

##### using 'ubek.py' #####

lo = ubek.Loader()
lo.loadLevel(1)
lo.makeEverything()
