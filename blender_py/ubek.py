import bpy,mathutils,json,bmesh,math,numbers,os,functools,random,inspect
from polygonizer import Polygonizer

class Loader:
    def __init__(self):
        # assuming the following layout:
        # project dir
        # +-+- blender_py <- we are here
        #   +- levels
        #   +- gfx
        dir = os.path.dirname(os.path.dirname(__file__))
        data = os.path.join(dir, 'data')
        self.levels_path = os.path.join(data, 'maps')
        self.textures_path = os.path.join(data, 'textures')
        # FC = floor/ceiling
        self.FC_SIZE = 256 # 1 floor tile = 256 ubek units
        self.SCALE = 256 # 256 ubek units = 1.0 in blender
        self.CEILING_Z = 0.75
        self.SPRITE_SCALE = 128/self.CEILING_Z
        self.CENTER = 256*128
        self.gfx_frames = True
        self.gfx_alpha = True
        self.gfx_emission = True
        self.ob_billboards = True
        self.ob_directional = True
        self.ob_walk = True
        self.anim_speed = 0.25
        self.texture_interpolation = 'Closest' # 'Linear'
        self.collection = 'ubek'
        self.world_brightness = 1
        self.world_brightness_influence = 5
        
        DEFAULT = (0.75,20) #threshold, strength
        
        self.emissive_textures = {'fabryka-leje':DEFAULT,'iskry':DEFAULT,'dach-fabr':DEFAULT,
        'sciana-fabr-okno':DEFAULT, 'fabryka-lampka':DEFAULT, 'sufit-lampy':DEFAULT,
        'lampka':(0.75,300), 'zapora':DEFAULT, 'cegly-kominek':(0.76,70),
        'lampka3':(0.90,500), 'dach-reaktor':DEFAULT, 'sciana-reakt-kamery':DEFAULT,
        'podbaza-sufit-lampy':DEFAULT, 'podbaza-sciana':(0.5,20), 'podbaza-sufit-czerw':DEFAULT,
        'podbaza-sciana-e':DEFAULT, 'sufit-ufo2':DEFAULT, 'sciana-ufo':DEFAULT,
        'sciana-ufo2':DEFAULT, 'sciana-ufo-c':DEFAULT, 'sciana-ufo-lampki':DEFAULT,
        'sciana-ufo-komp':(0.5,20), 'alien-lampa':DEFAULT, 'ufo-kula':(0.5,10),
        'alien-ziemia-sufit-l':DEFAULT, 'most-podloga-j':(0.75,5), 'most-podloga-lawa':(0.75,5),
        'ogien-m':(0,2), 'baza-alien-neon':DEFAULT, 'sufit-alien-l':DEFAULT,
        'sufit-alien':DEFAULT, 'czacha':DEFAULT, 'wajcha':DEFAULT, 'palnik&butla':(0.5,50),
        'podbaza-drzwi':(0.5,20), 'maszyna':(0.5,50), 'palnik':(0.5,50),
        'kulaognia':(0.5,10), 'sciana-alien-j':(0.9,100),
        'drzwi-alien':(0.9,20), 'drzwi-lampki':(0.9,20)}
        
        self.roughness_map = {'trawa':1, 'trawa-klomb':1, 'zielen':1, 'zielen-c':1,
         'zielen-psywon':1, 'zielen-c-niewej':1, 'plot':1, 'furtka':1,
         'sufit-norm':1, 'boazeria2':1, 'sciana':1, 'sciana1c':1, 'sciana1cc':1,
         'sciana1cc-szafka':1, 'sciana1ce':1, 'sciana1ce-alarm':1, 'sciana1-exit':1,
         'sciana1-kosci':1, 'sciana1-okno':1, 'sciana1-smiacz':1,
         'boazeria2-c':1, 'boazeria2-e':1, 'boazeria2-smie':1, 'boazeria2-balkon':1,
         'boazeria2-okno':1, 'boaz-szafka':1, 'rusbaza':1, 'rusbaza-c':1,
         'fala1':0.1, 'fala2':0.1, 'fala3':0.1, 'grunt':1, 'alien-grunt':1, 'alien-grunt-cj':1,
         'sufit':1, 'sufit-lampy':1, 'podloga':1, 'podloga-krew':1,
         'most-podloga':1, 'most-podloga-j':1, 'most-podloga-lawa':1,
         'most-sciana-j':1, 'most-sciana':1, 'most-drzwi':1,
         'alien-ziemia-c':1, 'alien-ziemia':1, 'alien-ziemia-sufit':1, 'baza-alien-dziura':1 }

    def loadLevel(self, number):
        self.loadFile(os.path.join(self.levels_path,f'plan{number}.json'))
        
    def loadFile(self, filename):
        with open(filename,'r') as f:
            self.loadData(json.load(f))
        
    def loadData(self, data):
        self.data = data
        self.afterLoadData()

    def afterLoadData(self):
        self.FC_COUNT = len(self.data["floor"])
        t = self.data['seg'][0]['dx']
        self.ceiling_type = (2 if (t & 2)!=0 else 1) if t>0 else 0
        self.floor_mats = dict()
        self.area_o = None
        self.billboard_cam = bpy.context.scene.camera
        self.collection_obj = None
        
    def getCollection(self):
        if self.collection:
            if self.collection_obj==None:
                self.collection_obj = bpy.data.collections.new(self.collection)
                bpy.context.scene.collection.children.link(self.collection_obj)
        return self.collection_obj if self.collection_obj else bpy.context.scene.collection
        
    def makeEverything(self):
        self.makeWorld()
        self.makeArea()
        self.makeFloor()
        self.makeCeiling()
        self.makeWalls()
        self.makeObjects()
        
    def xyFromTile(self,xy):
        return ((128-self.FC_COUNT/2)*256+256*xy[0], (128-self.FC_COUNT/2)*256+256*xy[1])

    def tileFromXY(self,xy):
        return (int(xy[0]/256 - (128-self.FC_COUNT/2)), int(xy[1]/256 - (128-self.FC_COUNT/2)))
        
    def fromUB2D(self,xy):
        return ((xy[0]-self.CENTER)/self.SCALE, (xy[1]-self.CENTER)/self.SCALE)
        
    def vertFrom2D(self,xy,z):
        return (xy[0],xy[1],z)
        
    def getGfx(self,i):
        if i<1 or i>len(self.data['gfx']):
            raise Exception('invalid gfx index '+str(i)
                +' (gfx has '+str(len(self.data['gfx']))+' items)')
        return self.data['gfx'][i-1]
    
    def findOrAddMaterial(self, ob, mats, ig, use, make_transparent=False, make_emission=False, walk_frame=False):
        if ig in mats:
            #print('find or add material '+str(ig)+' -> found '+str(mats[ig]))
            found = mats[ig]
            if found[2]==ob:
                return found[0]
            else:
                slot = len(ob.data.materials)
                ob.data.materials.append(found[1])
                return slot
        else:
            g = self.getGfx(ig)
            if (g["type"] & 2) != 0:
                make_transparent = True
            separate_alpha = ((g["type"] & 64) != 0)
            m = bpy.data.materials.new(g['name']+' gfx_'+str(ig))
            m.use_nodes = True
            bsdf = m.node_tree.nodes['Principled BSDF']
            if use=='SPRITE':
                bsdf.inputs[2].default_value=1 # roughness
            else:
                if g['name'] in self.roughness_map:
                    bsdf.inputs[2].default_value = self.roughness_map[g['name']]
            tex = m.node_tree.nodes.new('ShaderNodeTexImage')
            tex.interpolation = self.texture_interpolation
            tex.image = bpy.data.images.load(self.textures_path+'/'+g['name']+'.png')
            g['width'] = tex.image.size[0]
            g['height'] = tex.image.size[1]
            
            if g['name'] in self.emissive_textures:
                emission_params = self.emissive_textures[g['name']]
            else:
                emission_params =  None

            if use=='WALL':
                g['frames'] = int(g['width']/64)-1
                
            frames = g['frames'] if self.gfx_frames else 0
            multiple_frames = frames>0
            
            texco_result = None
            
            if use=='WALL' or multiple_frames or separate_alpha:
                texco = m.node_tree.nodes.new('ShaderNodeTexCoord')
                texco_result = (texco,2) #'UV'
            
            if use=='WALL':
                back_muladd = m.node_tree.nodes.new('ShaderNodeVectorMath')
                back_muladd.operation = 'MULTIPLY_ADD'
                back_muladd.inputs[1].default_value = (-1,1,1)
                back_muladd.inputs[2].default_value = (1/(1+frames),0,0)
                back_geo = m.node_tree.nodes.new('ShaderNodeNewGeometry')
                back_mix = m.node_tree.nodes.new('ShaderNodeMix')
                back_mix.data_type = 'VECTOR'
                m.node_tree.links.new(back_mix.inputs[0], back_geo.outputs[6]) # Backfacing -> mix.factor
                m.node_tree.links.new(back_mix.inputs[5], back_muladd.outputs[0]) # muladd -> mix.B
        
            if multiple_frames or separate_alpha:
                muladd = m.node_tree.nodes.new('ShaderNodeVectorMath')
                muladd.operation = 'MULTIPLY_ADD'
                muladd.inputs[1].default_value[0] = 1/(1+frames)
                muladd.inputs[1].default_value[1] = 0.5 if separate_alpha else 1
                muladd.inputs[1].default_value[2] = 1
                m.node_tree.links.new(muladd.inputs[0], texco.outputs['UV'])
                texco_result = (muladd,0)

            if use=='WALL':
                m.node_tree.links.new(back_mix.inputs[4], texco_result[0].outputs[texco_result[1]]) # -> mix.A
                m.node_tree.links.new(tex.inputs['Vector'], back_mix.outputs[1])
                m.node_tree.links.new(back_muladd.inputs[0], texco_result[0].outputs[texco_result[1]]) # -> muladd
            else:
                if texco_result:
                    m.node_tree.links.new(tex.inputs['Vector'], texco_result[0].outputs[texco_result[1]])
                
            if multiple_frames:
                directional = (g['type'] & 4)!=0
                frame_attr = m.node_tree.nodes.new('ShaderNodeAttribute')
                frame_attr.attribute_type='OBJECT'
                frame_attr.attribute_name='dir_frame' if directional and self.ob_directional else 'anim_frame'
                mul = m.node_tree.nodes.new('ShaderNodeMath')
                mul.operation = 'MULTIPLY'
                mul.inputs[1].default_value = 1/(1+frames)
                comb = m.node_tree.nodes.new('ShaderNodeCombineXYZ')
                if walk_frame:
                    walk_attr = m.node_tree.nodes.new('ShaderNodeAttribute')
                    walk_attr.attribute_type='OBJECT'
                    walk_attr.attribute_name='walk_frame'
                    walk_mod = m.node_tree.nodes.new('ShaderNodeMath')
                    walk_mod.operation = 'FLOORED_MODULO'
                    walk_mod.inputs[1].default_value = 2
                    walk_mul = m.node_tree.nodes.new('ShaderNodeMath')
                    walk_mul.operation = 'MULTIPLY'
                    walk_mul.inputs[1].default_value = 0.5
                    walk_add = m.node_tree.nodes.new('ShaderNodeMath')
                    walk_add.operation = 'ADD'
                    m.node_tree.links.new(walk_mod.inputs[0], walk_attr.outputs[0])
                    m.node_tree.links.new(walk_mul.inputs[0], walk_mod.outputs[0])
                    m.node_tree.links.new(walk_add.inputs[0], mul.outputs[0])
                    m.node_tree.links.new(walk_add.inputs[1], walk_mul.outputs[0])
                    m.node_tree.links.new(comb.inputs[0], walk_add.outputs[0])
                else:
                    m.node_tree.links.new(comb.inputs[0], mul.outputs[0])
                m.node_tree.links.new(mul.inputs[0], frame_attr.outputs[2])
                m.node_tree.links.new(muladd.inputs[2], comb.outputs[0])
                
            m.node_tree.links.new(bsdf.inputs['Base Color'], tex.outputs['Color'])
            out = m.node_tree.nodes['Material Output']
            if separate_alpha and self.gfx_alpha:
                add = m.node_tree.nodes.new('ShaderNodeVectorMath')
                add.operation = 'ADD'
                add.inputs[1].default_value[0] = 0
                add.inputs[1].default_value[1] = 0.5
                add.inputs[1].default_value[2] = 0
                m.node_tree.links.new(add.inputs[0], muladd.outputs[0])
                tex2 = m.node_tree.nodes.new('ShaderNodeTexImage')
                tex2.interpolation = self.texture_interpolation
                tex2.image = tex.image
                m.node_tree.links.new(tex2.inputs['Vector'], add.outputs[0])
                emis = m.node_tree.nodes.new('ShaderNodeEmission')
                trans = m.node_tree.nodes.new('ShaderNodeBsdfTransparent')
                mix = m.node_tree.nodes.new('ShaderNodeAddShader')
                m.node_tree.links.new(mix.inputs[0], emis.outputs[0])
                m.node_tree.links.new(mix.inputs[1], trans.outputs[0])
                m.node_tree.links.new(emis.inputs[0], tex.outputs[0])
                m.node_tree.links.new(trans.inputs[0], tex2.outputs[0])
                emis_strength = (emission_params[1] if emission_params else 10.0) if self.gfx_emission else 0.0
                emis.inputs[1].default_value = emis_strength
                m.node_tree.links.new(out.inputs[0], mix.outputs[0])
                m.shadow_method = 'CLIP'
                m.blend_method = 'BLEND'
            else:
                output_from = bsdf
                if emission_params and self.gfx_emission:
                    mix = m.node_tree.nodes.new('ShaderNodeMixShader')
                    emis = m.node_tree.nodes.new('ShaderNodeEmission')
                    emis.inputs[1].default_value = emission_params[1]
                    m.node_tree.links.new(emis.inputs[0], tex.outputs['Color'])
                    sep = m.node_tree.nodes.new('ShaderNodeSeparateColor')
                    sep.mode = 'HSV'
                    m.node_tree.links.new(sep.inputs[0], tex.outputs['Color'])
                    remap = m.node_tree.nodes.new('ShaderNodeMapRange')
                    remap.inputs[1].default_value = emission_params[0]
                    remap.inputs[2].default_value = emission_params[0]+0.01
                    m.node_tree.links.new(remap.inputs[0], sep.outputs[2])
                    m.node_tree.links.new(mix.inputs[0], remap.outputs[0])
                    m.node_tree.links.new(mix.inputs[1], bsdf.outputs[0])
                    m.node_tree.links.new(mix.inputs[2], emis.outputs[0])
                    m.node_tree.links.new(out.inputs[0], mix.outputs[0])
                    output_from = mix
                if make_transparent and self.gfx_alpha:
                    mix = m.node_tree.nodes.new('ShaderNodeMixShader')
                    trans = m.node_tree.nodes.new('ShaderNodeBsdfTransparent')
                    sep = m.node_tree.nodes.new('ShaderNodeSeparateColor')
                    sep.mode = 'HSV'
                    m.node_tree.links.new(sep.inputs[0], tex.outputs['Color'])
                    remap = m.node_tree.nodes.new('ShaderNodeMapRange')
                    remap.inputs[2].default_value = 1/255
                    m.node_tree.links.new(remap.inputs[0], sep.outputs[2])
                    m.node_tree.links.new(mix.inputs[0], remap.outputs[0])
                    m.node_tree.links.new(mix.inputs[1], trans.outputs[0])
                    m.node_tree.links.new(mix.inputs[2], output_from.outputs[0])
                    m.node_tree.links.new(out.inputs[0], mix.outputs[0])
                    m.shadow_method = 'CLIP'
                    m.blend_method = 'CLIP'
            slot = len(ob.data.materials)
            ob.data.materials.append(m)
            mats[ig] = (slot,m,ob)
            #print('find or add material '+str(ig)+' -> created in slot '+str(slot))
            return slot
        
    def getBoundingRect(self): # ((minx,miny),(maxx,maxy))
        return ((functools.reduce(min,(p["x"] for p in self.data['pts'])),
                functools.reduce(min,(p["y"] for p in self.data['pts']))),
                (functools.reduce(max,(p["x"] for p in self.data['pts'])),
                functools.reduce(max,(p["y"] for p in self.data['pts']))))

    def makeFloor(self):
        floor = self.makeTileArray('floor_mesh', self.getBoundingRect(), self.data['floor'], 0)
        if self.area_o:
            self.makeIntersection(floor, self.area_o)
        
    def makeCeiling(self):
        if self.ceiling_type > 0:
            ceiling = self.makeTileArray('ceiling_mesh', self.getBoundingRect(), self.data['ceiling'], self.CEILING_Z*self.ceiling_type)
            if self.area_o:
                self.makeIntersection(ceiling, self.area_o)

    def makeIntersection(self, o, cut):
        m = o.modifiers.new(type='BOOLEAN', name='Area intersection')
        m.operation = 'INTERSECT'
        m.solver = 'FAST'
        m.object = cut

    def makeTileArray(self, name, rect, arr, z):
        mesh_d = bpy.data.meshes.new(name+'_data')
        mesh_o = bpy.data.objects.new(name, mesh_d)
        self.getCollection().objects.link(mesh_o)
        floor_mats = dict()
        bm = bmesh.new()
        uv = bm.loops.layers.uv.new()
        tile_min, tile_max = self.tileFromXY(rect[0]), self.tileFromXY(rect[1])
        for x in range(tile_min[0],tile_max[0]+1):
            for y in range(tile_min[1],tile_max[1]+1):
                tile = arr[y % self.FC_COUNT][x % self.FC_COUNT]
                if tile>0:
                    p1 = self.fromUB2D(self.xyFromTile((x, y)))
                    p2 = self.fromUB2D(self.xyFromTile((x+1, y)))
                    p3 = self.fromUB2D(self.xyFromTile((x+1, y+1)))
                    p4 = self.fromUB2D(self.xyFromTile((x, y+1)))
                    v1 = bm.verts.new(self.vertFrom2D(p1, z))
                    v2 = bm.verts.new(self.vertFrom2D(p2, z))
                    v3 = bm.verts.new(self.vertFrom2D(p3, z))
                    v4 = bm.verts.new(self.vertFrom2D(p4, z))
                    f = bm.faces.new((v1, v2, v3, v4))
                    slot = self.findOrAddMaterial(mesh_o, floor_mats, tile, 'TILE')
                    f.material_index = slot
                    f.loops[0][uv].uv = (0,1)
                    f.loops[1][uv].uv = (1,1)
                    f.loops[2][uv].uv = (1,0)
                    f.loops[3][uv].uv = (0,0)
                    #print(p)
            bm.to_mesh(mesh_d)
        bm.free()
        return mesh_o

    def findOrAddV(self,bm,verts,ip,z):
        if ip in verts:
            return verts[ip]
        else:
            if ip<1 or ip>len(self.data['pts']):
                raise Exception('invalid pts index '+str(ip)
                    +' (pts has '+str(len(self.data['pts']))+' items)')
            pt = self.data['pts'][ip-1]
            p = self.fromUB2D((pt['x'],pt['y']))
            v = bm.verts.new(self.vertFrom2D(p,z))
            verts[ip] = v
            return v

    def makeWalls(self):
        mesh_d = bpy.data.meshes.new('walls_mesh_data')
        mesh_o = bpy.data.objects.new('walls_mesh',mesh_d)
        self.getCollection().objects.link(mesh_o)
        wall_mats = dict()
        bm = bmesh.new()
        uv = bm.loops.layers.uv.new()
        verts_floor = dict()
        verts_wall = dict()
        verts_high = dict()
        walls_col = None
        for i,w in enumerate(self.data['seg']):
            ip1 = w['p1']
            ip2 = w['p2']
            if ip1==ip2:
                print(f'seg#{i} p1==p2 {ip1}')
                continue
            is_high = (w['flags'] & 4) != 0
            z = 2*self.CEILING_Z if is_high else self.CEILING_Z
            gfx = self.getGfx(w['gfx'])
            animate = gfx['anim']
            frames = int(gfx['width']/64) # gfx['frames'] for walls is sometimes incorrect and ignored by the game
            separate_o = frames>1 or (w['flags'] & 2)!=0
            if separate_o: # multiple frames or door
                if not walls_col:
                    walls_col = bpy.data.collections.new('wall objects')
                    self.getCollection().children.link(walls_col)
                name = 'wall_'+str(i+1)
                tmp_mesh_d = bpy.data.meshes.new(name+'_data')
                tmp_mesh_o = bpy.data.objects.new(name,tmp_mesh_d)
                walls_col.objects.link(tmp_mesh_o)
                tmp_mats = dict()
                tmp_bm = bmesh.new()
                tmp_uv = tmp_bm.loops.layers.uv.new()
                tmp_verts_floor = dict()
                tmp_verts_wall = dict()
                tmp_verts_high = dict()
                tmp_wall_mats = dict()
                use_verts_floor = tmp_verts_floor                        
                use_verts_wall = tmp_verts_wall
                use_verts_high = tmp_verts_high
                use_bm = tmp_bm
                use_uv = tmp_uv
                use_mesh_o = tmp_mesh_o
                use_wall_mats = tmp_wall_mats
                self.addAnimFrame(tmp_mesh_o,'anim_frame',frames-1)
                if animate>0:
                    self.addAnimFrameDriver(tmp_mesh_o, 'anim_frame', animate, 1)
            else:
                tmp_bm = None
                use_verts_floor = verts_floor
                use_verts_wall = verts_wall
                use_verts_high = verts_high
                use_bm = bm
                use_uv = uv
                use_wall_mats = wall_mats
                use_mesh_o = mesh_o

            v1 = self.findOrAddV(use_bm,use_verts_floor,ip1,0)
            v2 = self.findOrAddV(use_bm,use_verts_high if is_high else use_verts_wall,ip1,z)
            v3 = self.findOrAddV(use_bm,use_verts_floor,ip2,0)
            v4 = self.findOrAddV(use_bm,use_verts_high if is_high else use_verts_wall,ip2,z)
            f = use_bm.faces.new((v1,v2,v4,v3))
            
            slot = self.findOrAddMaterial(use_mesh_o, use_wall_mats, w['gfx'], 'WALL')
            f.material_index = slot
            f.loops[0][use_uv].uv = (1,0)
            f.loops[1][use_uv].uv = (1,1)
            f.loops[2][use_uv].uv = (0,1)
            f.loops[3][use_uv].uv = (0,0)

            if separate_o:
                origin = v1.co
                tmp_bm.to_mesh(tmp_mesh_d)
                tmp_bm.free()
                tr = mathutils.Matrix.Translation(-origin)
                tmp_mesh_d.transform(tr)
                mw = tmp_mesh_o.matrix_world
                mw.translation = mw @ origin
            
        bm.to_mesh(mesh_d)
        bm.free()

    def addAnimFrame(self, ob, varname, maxframe):
        ob[varname] = 0
        ui = ob.id_properties_ui(varname)
        ui.update(min=0)
        if maxframe:
            ui.update(max=maxframe)

    def addAnimFrameDriver(self, ob, varname, maxframe, duration):
        anim = ob.driver_add('["'+varname+'"]')
        anim.driver.expression = f'fmod(frame*{self.anim_speed/duration}+{random.randint(0,maxframe)},{maxframe+1})'

    def addDirectionalFrameDriver(self, ob, parent, varname):
        dir = ob.driver_add('["'+varname+'"]')
        var = dir.driver.variables.new()
        var.name = 'cam_x'
        var.type='TRANSFORMS'
        var.targets[0].id = self.billboard_cam
        var.targets[0].transform_space = 'WORLD_SPACE'
        var.targets[0].transform_type = 'LOC_X'
        var = dir.driver.variables.new()
        var.name = 'cam_y'
        var.type='TRANSFORMS'
        var.targets[0].id = self.billboard_cam
        var.targets[0].transform_space = 'WORLD_SPACE'
        var.targets[0].transform_type = 'LOC_Y'
        var = dir.driver.variables.new()
        var.name = 'self_x'
        var.type='TRANSFORMS'
        var.targets[0].id = parent
        var.targets[0].transform_space = 'WORLD_SPACE'
        var.targets[0].transform_type = 'LOC_X'
        var = dir.driver.variables.new()
        var.name = 'self_y'
        var.type='TRANSFORMS'
        var.targets[0].id = parent
        var.targets[0].transform_space = 'WORLD_SPACE'
        var.targets[0].transform_type = 'LOC_Y'
        var = dir.driver.variables.new()
        var.name = 'self_az'
        var.type='TRANSFORMS'
        var.targets[0].id = parent
        var.targets[0].transform_space = 'WORLD_SPACE'
        var.targets[0].transform_type = 'ROT_Z'
        var.targets[0].rotation_mode = 'AUTO'
        dir.driver.expression = 'floor(fmod(4-4*(atan2(cam_y-self_y, cam_x-self_x)-self_az)/(pi*2)+0.5,4))'

    def makeObjects(self):
        ob_mats = dict()
        obj_col = bpy.data.collections.new('objects')
        self.getCollection().children.link(obj_col)
        for id,o in enumerate(self.data['ob']):
            if id<6: #ignore the first 6 objects (used for special purposes in the game)
                continue
            g = o['gfx']
            if g <= 0:
                continue
            try:
                gfx = self.getGfx(g)
                if (gfx['type'] & 256)!=0:
                    continue
                frames = gfx['frames'] if self.gfx_frames else 0
                multiple_frames = frames>0
                directional = multiple_frames and (gfx['type'] & 4)!=0
                animate = multiple_frames and gfx['anim']
                walk = (o['flags'] & 8)!=0 and self.ob_walk
                name = 'ob_'+str(id+1)
                sprite_name = name + '_sprite' if directional else name
                sprite_d = bpy.data.meshes.new(sprite_name+'_data')
                sprite_o = bpy.data.objects.new(sprite_name,sprite_d)
                obj_col.objects.link(sprite_o)
                varname = 'dir_frame' if directional and self.ob_directional else 'anim_frame'
                if multiple_frames:
                    self.addAnimFrame(sprite_o,varname,frames)
                    if animate>0:
                        self.addAnimFrameDriver(sprite_o, varname, animate, gfx['t']+1)
                    if walk:
                        self.addAnimFrame(sprite_o,'walk_frame',None)
                if directional and self.ob_directional:
                    ob = bpy.data.objects.new(name,None)
                    ob.empty_display_size = 0.3
                    ob.empty_display_type = 'ARROWS'
                    sprite_o.parent = ob
                    obj_col.objects.link(ob)
                    if self.billboard_cam:
                        self.addDirectionalFrameDriver(sprite_o, ob, varname)
                else:
                    ob = sprite_o
                slot = self.findOrAddMaterial(sprite_o, ob_mats, g, 'SPRITE', make_transparent=True, walk_frame=walk)
                # findOrAddMaterial() updates gfx[width/height]
                # so do it before calculating the final w, h, and z
                w = 2*gfx['width']/(frames+1)
                h = gfx['height']
                if (gfx['type'] & 64) != 0:
                    h /= 2
                z = o['z']
                if self.ceiling_type>0:
                    z = min(z,128*self.ceiling_type-h)                
                ob.location = self.vertFrom2D(self.fromUB2D((o['x'],o['y'])),z/self.SPRITE_SCALE)
                if ob != sprite_o:
                    sprite_o.location = (0,0,0)
                if self.ob_billboards and self.billboard_cam:
                    co = sprite_o.constraints.new(type='LOCKED_TRACK')
                    co.track_axis = 'TRACK_NEGATIVE_Y'
                    co.lock_axis = 'LOCK_Z'
                    co.target = self.billboard_cam
                bm = bmesh.new()
                uv = bm.loops.layers.uv.new()
                v1 = bm.verts.new((-w/2/self.SPRITE_SCALE,0,0))
                v2 = bm.verts.new((-w/2/self.SPRITE_SCALE,0,h/self.SPRITE_SCALE))
                v3 = bm.verts.new((w/2/self.SPRITE_SCALE,0,h/self.SPRITE_SCALE))
                v4 = bm.verts.new((w/2/self.SPRITE_SCALE,0,0))
                f = bm.faces.new((v1,v2,v3,v4))
                f.material_index = slot
                f.loops[0][uv].uv = (0,0)
                f.loops[1][uv].uv = (0,1)
                f.loops[2][uv].uv = (1,1)
                f.loops[3][uv].uv = (1,0)
                bm.to_mesh(sprite_d)
                bm.free()
            except:
                print('makeObject '+name+' g='+str(g))
                raise

    def makeWorld(self):
        name = os.path.basename('world_'+self.data['source_file'])
        w = bpy.data.worlds.new(name)
        w.use_nodes = True
        tex = w.node_tree.nodes.new('ShaderNodeTexImage')
        tex.image = bpy.data.images.load(os.path.join(self.textures_path, self.data['gfx'][1]['name']+'.png'))
        tex.projection = 'TUBE'
        tex.extension = 'EXTEND'
        rot = w.node_tree.nodes.new('ShaderNodeVectorRotate')
        rot.rotation_type = 'Z_AXIS'
        rot.inputs[3].default_value = math.radians(-45)
        muladd = w.node_tree.nodes.new('ShaderNodeVectorMath')
        muladd.operation = 'MULTIPLY_ADD'
        muladd.inputs[1].default_value = (-1,1,0.8)
        muladd.inputs[2].default_value = (0.5,0.5,0.5)
        texco = w.node_tree.nodes.new('ShaderNodeTexCoord')
        
        path = w.node_tree.nodes.new('ShaderNodeLightPath')
        mix = w.node_tree.nodes.new('ShaderNodeMix')
        mix.inputs[2].default_value = self.world_brightness_influence
        mix.inputs[3].default_value = self.world_brightness
        bg = w.node_tree.nodes['Background']
        
        w.node_tree.links.new(rot.inputs[0], texco.outputs[0])
        w.node_tree.links.new(tex.inputs[0], muladd.outputs[0])
        w.node_tree.links.new(muladd.inputs[0], rot.outputs[0])
        w.node_tree.links.new(mix.inputs[0], path.outputs[0])
        w.node_tree.links.new(bg.inputs[1], mix.outputs[0])
        w.node_tree.links.new(bg.inputs[0], tex.outputs[0])
        bpy.context.scene.world = w

    def debugPtsLabels(self):
        txt_col = bpy.data.collections.new('texts')
        self.getCollection().children.link(txt_col)
        for i,p in enumerate(self.data['pts']):
            t=self.debugText('p'+str(i),(p["x"],p["y"]),in_collection=txt_col,scale=0.2)
            t.show_in_front=True
                        
    def debugLine(self,vert_idxs):
        name = 'debug_line'
        mesh_d = bpy.data.meshes.new(name+'_mesh')
        mesh_o = bpy.data.objects.new(name,mesh_d)
        self.getCollection().objects.link(mesh_o)
        verts = []
        bm = bmesh.new()
        for i in vert_idxs:
            p = self.data['pts'][i]
            v = bm.verts.new(self.vertFrom2D(self.fromUB2D((p["x"],p["y"])), 0))
            verts.append(v)
        for i in range(len(verts)-1):
            bm.edges.new([verts[i],verts[i+1]])
        if len(verts)>1:
            bm.edges.new([verts[-1],verts[0]])
        bm.to_mesh(mesh_d)
        return mesh_o

    def makeArea(self):
        polymaker = Polygonizer(((p["x"],p["y"]) for p in self.data["pts"]),
                    ((s["p1"]-1, s["p2"]-1) for s in self.data["seg"]))
        poly = polymaker.findPolygon()
        if len(poly)==0:
            return
        name = 'area'
        mesh_d = bpy.data.meshes.new(name+'_mesh')
        mesh_o = bpy.data.objects.new(name,mesh_d)
        self.getCollection().objects.link(mesh_o)
        verts = []
        z_margin = 0.1
        bm = bmesh.new()
        for i in poly:
            p = self.data['pts'][i]
            v = bm.verts.new(self.vertFrom2D(self.fromUB2D((p["x"],p["y"])), -z_margin))
            verts.append(v)
        f = bm.faces.new(verts)
        r = bmesh.ops.extrude_face_region(bm, geom=[f])
        everts = [e for e in r['geom'] if isinstance(e, bmesh.types.BMVert)]
        bmesh.ops.translate(bm, vec=(0,0,2*z_margin+2*self.CEILING_Z), verts=everts)
        bm.to_mesh(mesh_d)
        mesh_o.hide_render = True
        mesh_o.hide_viewport = True
        self.area_o = mesh_o
        return mesh_o
        
    def debugText(self,txt,p=None,z=0,in_collection=None, scale=None):
        name = 'debug_text'
        cu = bpy.data.curves.new(type="FONT", name="Font Curve")
        cu.body = txt
        ob = bpy.data.objects.new(name=name, object_data=cu)
        if in_collection:
            in_collection.objects.link(ob)
        else:
            self.getCollection().objects.link(ob)
        if p:
            ob.location = self.vertFrom2D(self.fromUB2D(p),z if z else 0)
        if scale:
            ob.scale = (scale,scale,scale) if isinstance(scale,numbers.Number) else scale
        return ob
