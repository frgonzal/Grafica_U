import libs.transformations as tr
import numpy as np
from libs.scene_graph import findNode
from libs.basic_shapes import createTextureNormalsCube
from libs.assets_path import getAssetPath
from libs.gpu_shape import createGPUShape
from libs.shaders import textureSimpleSetup
from OpenGL.GL import *

def generateT(t):
    return np.array([[1, t, t**2, t**3]]).T
def hermiteMatrix(P1, P2, T1, T2):
    G = np.concatenate((P1, P2, T1, T2), axis=1)
    Mh = np.array([[1, 0, -3, 2], [0, 0, 3, -2], [0, 1, -2, 1], [0, 0, -1, 1]])
    return np.matmul(G, Mh)
def bezierMatrix(P0, P1, P2, P3):
    G = np.concatenate((P0, P1, P2, P3), axis=1)
    Mb = np.array([[1, -3, 3, -1], [0, 3, -6, 3], [0, 0, 3, -3], [0, 0, 0, 1]])
    return np.matmul(G, Mb)
def evalCurve(M, N):
    ts = np.linspace(0.0, 1.0, N)
    curve = np.ndarray(shape=(N, 3), dtype=float)
    for i in range(len(ts)):
        T = generateT(ts[i])
        curve[i, 0:3] = np.matmul(M, T).T
    return curve



class Camera:
    def __init__(self,controller, width , height,):
        dim = controller.dim
        div = controller.div
        self.eye = np.array([-dim, dim, dim])
        self.at  = np.array([ 0.0, 0.0, 0.0])
        self.up  = np.array([ 0.0, 1.0, 0.0])

        self.projection = tr.ortho(-dim*div, dim*div, -dim, dim, 0.1, 100)
        self.view = tr.lookAt(self.eye, self.at, self.up)

    def update(self, controller, nave):
        #mirar siempre desde una de las esquinas del cubo
        self.eye = np.array([nave.positionX - controller.dim,
                             nave.positionY + controller.dim,
                             nave.positionZ + controller.dim])
        self.at  = np.array([nave.positionX,
                             nave.positionY,
                             nave.positionZ])
        self.view = tr.lookAt(self.eye, self.at, self.up)

class Nave:
    def __init__(self,max_speed,max_angular_speed):
        self.positionX = 0
        self.positionZ = 0
        self.positionY = 0
        self.speed     = 0

        self.theta         = 0
        self.angular_speed = 0
        self.phi           = 0

        self.max_speed = max_speed
        self.max_angular_speed = max_angular_speed

    def update(self,controller,grafo,dt):
        speed = self.speed*self.max_speed
        angular_speed = self.angular_speed*self.max_angular_speed
        self.theta += dt*angular_speed*np.pi/8

        self.positionX += dt*speed*np.cos(self.theta)*np.cos(self.phi)
        self.positionY += dt*speed*np.sin(self.phi)
        self.positionZ += dt*speed*np.sin(self.theta)*np.cos(self.phi)

        naves = findNode(grafo,"escuadron")
        naves.transform = tr.translate(self.positionX,
                                       self.positionY,
                                       self.positionZ)

        nave = findNode(grafo, "nave")
        nave.transform = tr.matmul([tr.rotationY(-self.theta),
                                    tr.rotationZ(self.phi)])

        sombraEscuadron = findNode(grafo, "sombraEscuadron")
        sombraEscuadron.transform = tr.matmul([tr.translate(self.positionX, -0.4, self.positionZ)])

        sombra = findNode(grafo,"sombra")
        sombra.transform = tr.matmul([tr.scale(1.0, 0.01, 1.0),
                                      tr.rotationY(-self.theta),
                                      tr.rotationZ(self.phi),
                                      tr.rotationY(np.pi/2), tr.uniformScale(0.2)])

class Ruta:
    def __init__(self,pipeline):
        self.ruta = []
        self.tiempo = []
        self.dir = []

        self.cubo = createGPUShape(pipeline, createTextureNormalsCube(1,1,1,1))
        self.cubo.texture = textureSimpleSetup(getAssetPath("RED.png"), GL_REPEAT, GL_REPEAT, GL_NEAREST, GL_NEAREST)

        self.cubo2 = createGPUShape(pipeline, createTextureNormalsCube(1,1,1,1))
        self.cubo2.texture = textureSimpleSetup(getAssetPath("BLUE.jpg"), GL_REPEAT, GL_REPEAT, GL_NEAREST, GL_NEAREST)

        self.grabar  = False
        self.dibujar = False
        self.reprod  = False
        self.N       = 0
        self.HermiteCurve = np.zeros((0,3))
        self.dirHermiteCurve = np.zeros((0,3))

    def iniciar_grabacion(self,nave,time):
        self.N = 0
        self.reprod = False
        self.grabar = True
        self.ruta = [[nave.positionX,nave.positionY,nave.positionZ]]
        self.tiempo = [time]
        self.dir = [[nave.theta,nave.phi]]
        self.HermiteCurve = np.zeros((0,3))
        self.dirHermiteCurve = np.zeros((0,3))

    def actualizar(self,nave,time):
        self.ruta.append([nave.positionX,nave.positionY,nave.positionZ])
        self.tiempo.append(time)
        self.dir.append([nave.theta,nave.phi])
        self.estado()
        
        if len(self.ruta)>2:
            ref = 60
            #posiciones
            P1 = np.array([[self.ruta[-3][0], self.ruta[-3][1], self.ruta[-3][2]]]).T
            P2 = np.array([[self.ruta[-2][0], self.ruta[-2][1], self.ruta[-2][2]]]).T
            tan = nave.speed*np.sqrt(np.square(self.ruta[-2][0]-self.ruta[-3][0])+np.square(self.ruta[-2][1]-self.ruta[-3][1])+np.square(self.ruta[-2][2]-self.ruta[-3][2]))
            T1 = np.array([[tan*np.cos(self.dir[-3][0])*np.cos(self.dir[-2][1]),
                            tan*np.sin(self.dir[-3][1]),
                            tan*np.sin(self.dir[-3][0])*np.cos(self.dir[-3][1])]]).T
            T2 = np.array([[tan*np.cos(self.dir[-2][0])*np.cos(self.dir[-2][1]),
                            tan*np.sin(self.dir[-2][1]),
                            tan*np.sin(self.dir[-2][0])*np.cos(self.dir[-2][1])]]).T
            GMh = hermiteMatrix(P1, P2, T1, T2)
            HermiteCurve = evalCurve(GMh, int(ref*(self.tiempo[-2]-self.tiempo[-3])))
            self.HermiteCurve = np.concatenate((self.HermiteCurve,HermiteCurve),axis=0)
            #direcciones
            P1 = np.array([[self.dir[-3][0], self.dir[-3][1], 0.0]]).T
            P2 = np.array([[self.dir[-2][0], self.dir[-2][1], 0.0]]).T
            T1 = np.array([[self.dir[-2][0]-self.dir[-3][0],self.dir[-2][1]-self.dir[-3][1], 0.0]]).T
            T2 = np.array([[self.dir[-1][0]-self.dir[-2][0],self.dir[-1][1]-self.dir[-2][1], 0.0]]).T
            GMh = hermiteMatrix(P1, P2, T1, T2)
            HermiteCurve = evalCurve(GMh, int(ref*(self.tiempo[-2]-self.tiempo[-3])))
            self.dirHermiteCurve = np.concatenate((self.dirHermiteCurve,HermiteCurve),axis=0)

    def reproducir(self,nave,iniciar = False):
        if iniciar and len(self.HermiteCurve)>0:
            self.reprod = True
            self.grabar = False
        if self.reprod:
            if self.N>len(self.HermiteCurve)-1: self.N = 0
            nave.positionX = self.HermiteCurve[self.N][0]
            nave.positionY = self.HermiteCurve[self.N][1]
            nave.positionZ = self.HermiteCurve[self.N][2]
            nave.theta     = self.dirHermiteCurve[self.N][0]
            nave.phi       = self.dirHermiteCurve[self.N][1]
            self.N+=1

    def estado(self):
        if len(self.ruta)!=0:
            print("punto agregado: ",self.ruta[-1],end=", ")
            print("orientacion:", self.dir[-1],end=", ")
            print("total de puntos: ", len(self.ruta))

    def draw(self,pipeline):
        if self.dibujar:
            for posicion in self.ruta:
                model = tr.matmul([tr.translate(posicion[0],posicion[1],posicion[2]),
                                tr.uniformScale(0.2)])
                glUniformMatrix4fv(glGetUniformLocation(pipeline.shaderProgram, "model"), 1, GL_TRUE, model)
                pipeline.drawCall(self.cubo)
            for i,pos in enumerate(self.HermiteCurve):
                if i%2==0:
                    model = tr.matmul([tr.translate(pos[0],pos[1],pos[2]),
                                    tr.uniformScale(0.05)])
                    glUniformMatrix4fv(glGetUniformLocation(pipeline.shaderProgram, "model"), 1, GL_TRUE, model)
                    pipeline.drawCall(self.cubo2)

#Este Grupo solo da vueltas
class Obstaculos:
    def __init__(self,controller,nodo,escala):
        self.nodo   = nodo
        self.escala = escala
        self.speedZ = np.random.random()*6
        self.positionX = np.random.randint(-controller.largoMapa/2,controller.largoMapa/2)
        self.positionZ = np.random.randint(-controller.anchoMapa/2,controller.anchoMapa/2)
        self.positionY = np.random.randint(2, 4)
        self.speedrotationX = np.random.random()*2
        self.speedrotationY = np.random.random()*2
        self.speedrotationZ = np.random.random()*2

    def update(self,controller,grafo,dt):

        self.positionZ += dt*self.speedZ
        if self.positionZ > controller.anchoMapa/2 and self.speedZ > 0:
            self.speedZ = -self.speedZ
        elif self.positionZ < -controller.anchoMapa/2 and self.speedZ < 0:
            self.speedZ = -self.speedZ
            
        objeto = findNode(grafo, self.nodo)
        objeto.transform = tr.matmul([tr.translate(self.positionX, self.positionY, self.positionZ),
                                      tr.rotationX(self.speedrotationX*controller.total_time),
                                      tr.rotationY(self.speedrotationY*controller.total_time),
                                      tr.rotationZ(self.speedrotationZ*controller.total_time),
                                      tr.uniformScale(self.escala)])

#grupo con posiciones aleatorias pero estaticas
class MurosMapa:
    def __init__(self,controller,densidad,altura_max,largo_max):
        self.total = 0
        posiciones = []
        for i in range(controller.largoMapa):
            for j in range(controller.anchoMapa):
                if np.random.random() < densidad:
                    posiciones.append([i, j, int(1 + np.random.random()*altura_max), int(1+np.random.random()*largo_max)])
                    self.total += 1
        self.posiciones = np.array(posiciones)


#Grupo con todo aleatorio
class Meteoritos:
    def __init__(self,controller,nodo,total):
        self.nodo = nodo
        self.total = total
        self.meteoritos = np.zeros((total,9),dtype=float)
        for i in range(total):
            self.meteoritos[i][0] = (0.5-np.random.random())*controller.largoMapa #X
            self.meteoritos[i][1] = np.random.randint(20,50)                                       #Y
            self.meteoritos[i][2] = (0.5-np.random.random())*controller.anchoMapa #Z

            self.meteoritos[i][3] = (0.5-np.random.random())*3     #SpeedX
            self.meteoritos[i][4] = -10 -np.random.random()* 10    #SpeedY
            self.meteoritos[i][5] = (0.5-np.random.random())*1     #SpeedZ

            self.meteoritos[i][6] = np.random.random()*np.pi #angular_speedX
            self.meteoritos[i][7] = np.random.random()*np.pi #Y
            self.meteoritos[i][8] = np.random.random()*np.pi #Z
    
    def update(self,controller,grafo,dt):
        for i in range(self.total):    
            self.meteoritos[i][0] += dt*self.meteoritos[i][3]

            if self.meteoritos[i][1] < -1: 
                self.meteoritos[i][0]  = (0.5-np.random.random())*controller.largoMapa
                self.meteoritos[i][1]  = np.random.randint(70,120)
                self.meteoritos[i][2]  = (0.5-np.random.random())*controller.anchoMapa
            else:                 
                self.meteoritos[i][1] += dt*self.meteoritos[i][4]

            self.meteoritos[i][2] += dt*self.meteoritos[i][5]

            meteoritoG = findNode(grafo, self.nodo+str(i))
            meteoritoG.transform = tr.matmul([tr.translate(self.meteoritos[i][0], self.meteoritos[i][1], self.meteoritos[i][2]),
                                              tr.rotationX(self.meteoritos[i][6]*controller.total_time),
                                              tr.rotationY(self.meteoritos[i][7]*controller.total_time),
                                              tr.rotationZ(self.meteoritos[i][8]*controller.total_time),
                                              tr.scale(1.0,0.5,1.0)])
