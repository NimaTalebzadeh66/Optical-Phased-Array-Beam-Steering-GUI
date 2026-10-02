"""Interactive scalar OPA dashboard. Run python opa_gui.py; --check tests model."""
import sys
import numpy as np

def simulate(nx, ny, pitch, theta, phi, pattern, width, sigma, seed, angles):
    x,y=np.meshgrid((np.arange(nx)-(nx-1)/2)*pitch,(np.arange(ny)-(ny-1)/2)*pitch)
    pos=np.column_stack((x.ravel(),y.ravel()))
    t,p=np.radians([theta,phi]); steer=np.array([np.sin(t)*np.cos(p),np.sin(t)*np.sin(p)])
    errors=np.random.default_rng(seed).normal(0,np.radians(sigma),len(pos))
    phases=-2*np.pi*(pos@steer)+errors
    def field(ux,uy):
        ux,uy=np.broadcast_arrays(ux,uy); out=np.zeros(ux.shape,complex)
        for r,ph in zip(pos,phases): out+=np.exp(1j*(2*np.pi*(r[0]*ux+r[1]*uy)+ph))
        radius=np.sqrt(ux**2+uy**2); polar=np.degrees(np.arcsin(np.clip(radius,0,1)))
        g=np.ones_like(radius)
        if pattern=='Gaussian': g=np.exp(-(polar/width)**2)
        elif pattern=='Cosine': g=np.sqrt(np.clip(1-radius**2,0,1))
        elif pattern=='Sinc aperture': g=np.sinc(ux)*np.sinc(uy)
        return np.where(radius<=1+1e-12,g*out/len(pos),0)
    a=np.radians(angles)
    cut=np.abs(field(np.sin(a)*np.cos(p),np.sin(a)*np.sin(p)))**2
    return pos,phases,field,cut

def checks():
    args=(3,1,.5,30,0,'Uniform',30,0,12,np.array([0,30]))
    _,_,f,c=simulate(*args)
    assert np.allclose(c,[1/9,1])
    _,_,f,c=simulate(3,1,.5,30,0,'Gaussian',30,0,12,np.array([30]))
    assert np.allclose(c,[np.exp(-2)])
    _,_,f,c=simulate(4,4,.5,20,40,'Uniform',30,0,12,np.array([20]))
    assert np.allclose(c,[1])
    print('Model checks passed: three-element cancellation, Gaussian weighting, planar steering.')

if '--check' in sys.argv:
    checks(); sys.exit()

import tkinter as tk
from tkinter import ttk, filedialog
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

root=tk.Tk(); root.title('OPA Beam Steering Laboratory'); root.geometry('1450x900'); root.configure(bg='#081321')
style=ttk.Style(); style.theme_use('clam')
style.configure('TFrame',background='#081321'); style.configure('TLabel',background='#081321',foreground='#e7eff9')
style.configure('TButton',padding=7)
side=ttk.Frame(root,padding=15); side.pack(side='left',fill='y')
ttk.Label(side,text='OPA LAB',font=('Arial',21,'bold')).pack(anchor='w')
ttk.Label(side,text='Scalar far-field model • upper hemisphere').pack(anchor='w',pady=(0,15))
controls={}; pending=None

def schedule(*_):
    global pending
    if pending: root.after_cancel(pending)
    pending=root.after(180,update)

def slider(name,lo,hi,value,res=1):
    ttk.Label(side,text=name).pack(anchor='w',pady=(8,0))
    var=tk.DoubleVar(value=value); controls[name]=var
    tk.Scale(side,from_=lo,to=hi,resolution=res,orient='horizontal',variable=var,command=schedule,length=245,bg='#081321',fg='#e7eff9',highlightthickness=0,troughcolor='#213149').pack()
slider('Antennas X',1,20,8); slider('Antennas Y',1,20,8)
slider('Pitch / wavelength',.25,2,.5,.05)
slider('Steering theta (deg)',0,75,20,.5); slider('Steering phi (deg)',0,360,0,1)
slider('Gaussian field width (deg)',5,90,30,1); slider('Phase error std (deg)',0,60,0,1)
pattern=tk.StringVar(value='Uniform')
ttk.Label(side,text='Individual antenna field pattern').pack(anchor='w',pady=(8,0))
combo=ttk.Combobox(side,textvariable=pattern,values=['Uniform','Gaussian','Cosine','Sinc aperture'],state='readonly'); combo.pack(fill='x'); combo.bind('<<ComboboxSelected>>',schedule)
seed=tk.IntVar(value=12)
def resample(): seed.set(seed.get()+1); schedule()
ttk.Button(side,text='New phase-error realization',command=resample).pack(fill='x',pady=8)
status=tk.StringVar(); ttk.Label(side,textvariable=status,wraplength=255).pack(anchor='w',pady=10)
ttk.Label(side,text='λ = 1550 nm. Equal unit excitations.\nIntensity reference: N².\nPatterns have unit boresight field.\nNo coupling, losses or polarization.\n3D radius represents intensity,\nnot a propagating wavefront.',wraplength=255).pack(anchor='w')
fig=Figure(figsize=(11,8),facecolor='#081321',layout='constrained')
axes=[fig.add_subplot(221,projection='3d'),fig.add_subplot(222),fig.add_subplot(223),fig.add_subplot(224)]
canvas=FigureCanvasTkAgg(fig,master=root); canvas.get_tk_widget().pack(side='right',fill='both',expand=True)
angles=np.linspace(-90,90,1801)

def update():
    global pending
    pending=None
    vals={k:v.get() for k,v in controls.items()}
    nx=int(vals['Antennas X']); ny=int(vals['Antennas Y']); pitch=vals['Pitch / wavelength']; theta=vals['Steering theta (deg)']; phi=vals['Steering phi (deg)']
    pos,phases,field,cut=simulate(nx,ny,pitch,theta,phi,pattern.get(),vals['Gaussian field width (deg)'],vals['Phase error std (deg)'],seed.get(),angles)
    for ax in axes:
        ax.clear(); ax.set_facecolor('#0e1d30'); ax.tick_params(colors='#c1d1e4',labelsize=8)
        ax.title.set_color('white'); ax.xaxis.label.set_color('#c1d1e4'); ax.yaxis.label.set_color('#c1d1e4')
    t,p=np.meshgrid(np.linspace(0,np.pi/2,46),np.linspace(0,2*np.pi,91))
    ux=np.sin(t)*np.cos(p); uy=np.sin(t)*np.sin(p); uz=np.cos(t); intensity=np.abs(field(ux,uy))**2
    axes[0].plot_surface(intensity*ux,intensity*uy,intensity*uz,facecolors=matplotlib.colormaps['turbo'](intensity),rstride=1,cstride=1,linewidth=0,shade=False)
    axes[0].set(xlim=(-1,1),ylim=(-1,1),zlim=(0,1),xlabel='I ux',ylabel='I uy',zlabel='I uz',title='3D relative intensity'); axes[0].set_box_aspect((2,2,1))
    q=np.linspace(-1,1,121); U,V=np.meshgrid(q,q); valid=U**2+V**2<=1
    db=10*np.log10(np.maximum(np.abs(field(U,V))**2,1e-4)); db=np.ma.array(db,mask=~valid)
    axes[1].imshow(db,origin='lower',extent=(-1,1,-1,1),vmin=-40,vmax=0,cmap='turbo')
    st=np.radians(theta); sp=np.radians(phi); axes[1].plot(np.sin(st)*np.cos(sp),np.sin(st)*np.sin(sp),'w+',markersize=12)
    axes[1].set(xlabel='ux = sin θ cos φ',ylabel='uy = sin θ sin φ',title='Beam map • dB, fixed reference (−40 to 0)')
    axes[2].imshow(np.degrees(np.angle(np.exp(1j*phases))).reshape(ny,nx),origin='lower',vmin=-180,vmax=180,cmap='twilight',aspect='auto')
    axes[2].set(xlabel='Antenna X index',ylabel='Antenna Y index',title='Applied phase including errors • −180° to 180°')
    axes[3].plot(angles,10*np.log10(np.maximum(cut,1e-6)),color='#36dfec'); axes[3].axvline(theta,color='#ffb55b',linestyle='--')
    axes[3].set(xlim=(-90,90),ylim=(-40,1),xlabel='Signed cut angle (deg)',ylabel='Relative intensity (dB)',title=f'Cut through commanded azimuth φ = {phi:g}°'); axes[3].grid(alpha=.15)
    peak=angles[np.argmax(cut)]; target=float(np.abs(field(np.sin(st)*np.cos(sp),np.sin(st)*np.sin(sp)))**2)
    status.set(f'{nx*ny} antennas • pitch {pitch*1550:.0f} nm\nCommand: θ {theta:g}°, φ {phi:g}°\nIntensity at command: {target:.4f}\nCut peak angle: {peak:.1f}°\nCut peak intensity: {cut.max():.4f}\nSeed: {seed.get()}\nCut peak is not a global 3D search.')
    canvas.draw_idle()

def export():
    path=filedialog.asksaveasfilename(defaultextension='.png',filetypes=[('PNG image','*.png')])
    if path: fig.savefig(path,dpi=200,facecolor=fig.get_facecolor())
ttk.Button(side,text='Export dashboard PNG',command=export).pack(fill='x',pady=8)
update(); root.mainloop()
