import math

class Polygonizer:
    class P:
        def __init__(self,idx,x,y):
            self.idx=idx
            self.x=x
            self.y=y
            self.seg=[]
            
        def __repr__(self):
            return 'P'+str(self.idx)+'('+str(self.x)+' '+str(self.y)+' s='+str(list((s.idx for s in self.seg)))+')'
            
    class S:
        def __init__(self,idx,p1,p2):
            self.idx=idx
            self.p1=p1
            self.p2=p2
            self.dir=999

        def beginP(self,dir):
            return self.p1 if dir else self.p2
            
        def endP(self,dir):
            return self.p2 if dir else self.p1
        
        def __repr__(self):
            return 'S'+str(self.idx)+'('+str(self.p1.idx)+' '+str(self.p2.idx)+' d='+str(self.dir)+')'
        
        def calculateDirection(self):
            return math.atan2(self.p2.x-self.p1.x, self.p2.y-self.p1.y)

    def __init__(self,pts,seg):
        self.pts=[]
        for (i,in_p) in enumerate(pts):
            self.pts.append(self.P(i,in_p[0],in_p[1]))
            
        self.seg=[]
        for (i,in_s) in enumerate(seg):
            p1=self.pts[in_s[0]]
            p2=self.pts[in_s[1]]
            s=self.S(i, p1, p2)
            self.seg.append(s)
            p1.seg.append(s)
            p2.seg.append(s)
            s.dir=s.calculateDirection()

        for p in self.pts:
            p.seg.sort(key=lambda s: ((s.dir+math.pi*2) if s.p1==p else (s.dir+math.pi)) % (math.pi*2) - math.pi)

    class Ctx:
        def __init__(self, seg, dir, turn):
            self.path=[(seg,dir)]
            self.turn = turn
            self.longest_loop = []
        
        def run(self):
            last=self.path[-1]
            while True:
                p=last[0].endP(last[1])
                #print('last=',last,'p=',p)
                go=self.choosePath(p,last[0])
                #print('go',go)
                if go:
                    found = self.findSegmentInPath(go[0])
                    #print('found=',found)
                    if found != None:
                        #print('path=',self.path)
                        if self.path[found][1]==go[1]:
                            self.foundLoop(self.path[:found])
                            self.path = self.path[found:]
                            #print('same dir, break')
                            break
                        else:
                            #print('reverse dir, remove [:',found,']')
                            self.foundLoop(self.path[found+1:])
                            self.path=self.path[:found]
                            if len(self.path)==0:
                                break
                            last = go
                            continue
                    self.path.append(go)
                    last = go
                else:
                    break
            self.foundLoop(self.path)

        def findSegmentInPath(self,s):
            for i,e in enumerate(self.path):
                if e[0]==s:
                    return i
            return None

        def choosePath(self, p, coming_from_seg):
            # return what segment to visit next
            #print('choosePath, p=',p)
            N=len(p.seg)
            i=p.seg.index(coming_from_seg)
            s=p.seg[(i+1 if self.turn else i+N-1) % N]
            dir = s.p1==p
            return (s,dir)
        
        def foundLoop(self,loop):
            #print(f'foundLoop({len(loop)}) {loop}')
            if len(loop)>len(self.longest_loop):
                #print('...becomes longest_loop')
                self.longest_loop = loop
            
    def findPolygonInternal(self, start_seg, dir, turn):
        ctx = self.Ctx(self.seg[start_seg],dir,turn)
        ctx.run()
        return list((path_e[0].beginP(path_e[1]).idx for path_e in ctx.longest_loop))

    def findPolygonStartingAt(self, start_seg, dir):
        #print(f'findPolygonStartingAt {start_seg} {dir}')
        p1 = self.findPolygonInternal(start_seg, dir, True)
        p2 = self.findPolygonInternal(start_seg, dir, False)
        a1 = self.polygonArea(p1)
        a2 = self.polygonArea(p2)
        #print(f'a1={a1}  a2={a2}')
        return p1 if a1>a2 else p2
    
    def polygonArea(self,poly):
        area = 0
        N = len(poly)
        for i in range(N):
            p = self.pts[poly[i]]
            pn = self.pts[poly[(i+1)%N]]
            area += p.x*pn.y - pn.x*p.y
        return abs(area/2)
    
    def findEdgePoint(self):
        found=self.pts[0]
        for p in self.pts:
            if p.x>found.x:
                found=p
        return found

    def findPolygon(self):
        s = self.findEdgePoint().seg[0].idx
        #print(f'findPolygon s={s}')
        p1 = self.findPolygonStartingAt(s,True)
        p2 = self.findPolygonStartingAt(s,False)
        a1 = self.polygonArea(p1)
        a2 = self.polygonArea(p2)
        #print(f'findPolygon a1={a1}  a2={a2}')
        return p1 if a1>a2 else p2
