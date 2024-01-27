# ubek-in-blender
This little python script imports the levels from the 1995 Amiga game "Ubek" into Blender.

The effect is shown in this youtube video: https://youtu.be/zmdKzVL3jFI

Not a true addon, sorry... But with so very limited audience and usefulness there is little incentive for doing anything more than a quick and dirty script that does its work. And actually, calling such experimental code from the scripting text editor can be even quite convenient, especially when simultaneously tweaking the ubek.py source (hint: import reload; reload(ubek))

`data/textures` contains all in-game textures converted to PNG.

`data/maps` has all 18 original game levels converted to JSON for easy parsing.

### Usage ###
* go to the `Scripting` workspace in Blender
* load `test.py` located in the `blender_py` directory
* run the script.
* the Loader object is somewhat configurable, that means you can change some defaults after loading the level but before calling makeEverything()
* look into `ubek.py` to see what can be changed
* all objects are added to the collection called `ubek` for your convenience (easily deletable with a single right click "Delete hierarchy" before trying another level or different options)

### Known bugs ###
* The Floor and ceiling objects are built from rectangular grids of tiles, cut to the actual level area using the boolean modifier. Amazingly, in some maps the boolean operation produces incorrect result ("leaky" floor or ceiling) when the `Fast` calculation mode is used, while in the other levels the 'Fast' mode works correctly and the supposedly better `Exact` mode can't do the thing. So, just switch to another mode if something is wrong.
