import sys,os
import re
import pkg_resources
required  = {'tkcalendar', 'pandas', 'matplotlib'} 
#installed = {pkg.key for pkg in pkg_resources.working_set}
#missing   = required - installed


try:
    import tkinter as tk
    from tkinter import ttk
    from tkinter import filedialog as fd
    from tkinter.messagebox import showerror, showwarning
    from datetime import datetime, timedelta
    from functools import reduce
    import data_grabber
    import config

    from tkcalendar import Calendar, DateEntry

    from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
    from matplotlib.figure import Figure
    import matplotlib.colors as mcolors
    from matplotlib import pyplot as plt
    import matplotlib.ticker as mt

    import pandas as pd

except ImportError:

    installed = {pkg for pkg in sys.modules.keys()}
    missing   = required - installed
    sys.exit('''Missing dependencies. First run 
    pip install %s '''%(' '.join(missing)))

class MainFrame(ttk.Frame):
    def __init__(self, container):
        super().__init__(container)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        self.cfg=config.config()
        self.acnet_devs={}
        
        devlist_scroll=tk.Scrollbar(self)
        self.devlist=ttk.Treeview(self,yscrollcommand=devlist_scroll.set)
        devlist_scroll.config(command=self.devlist.yview)
        devlist_scroll.grid(column=1,row=0,sticky=tk.N+tk.S)
        self.devlist['columns']=('device','node','event')
        self.devlist.column("#0",width=0,stretch=tk.NO)
        self.devlist.column("device",anchor=tk.CENTER,width=40)
        self.devlist.column("node",anchor=tk.CENTER,width=40)
        self.devlist.column("event",anchor=tk.CENTER,width=40)
        self.devlist.heading("#0",text="",anchor=tk.CENTER)
        self.devlist.heading("device",text="Device",anchor=tk.CENTER)
        self.devlist.heading("node",text="Node",anchor=tk.CENTER)
        self.devlist.heading("event",text="Event",anchor=tk.CENTER)
        self.devlist.grid(column=0,row=0,sticky = tk.NSEW)
        
        self.devcell = tk.Frame(self)
        self.devcell.grid(column=0,row=1,columnspan=2, sticky= tk.W + tk.E, padx=10,pady=10)
        self.devcell.grid_columnconfigure(0,weight=1)
        self.devcell.grid_columnconfigure(1,weight=1)

        self.device = ttk.Combobox(self.devcell, values=[], justify='left')
        self.device.set('Device')
        self.device.grid(column=0,row=0,sticky=tk.W+tk.E)
        self.device.bind("<KeyRelease>",self.fill_device)
        self.device.bind("<FocusIn>",lambda x: self.device.selection_range(0, tk.END))
        self.device.bind("<FocusOut>",self.fill_node_event)

        self.node = ttk.Combobox(self.devcell, values=[], justify='left')
        self.node.set('Node\tEvent')
        self.node.grid(column=1,row=0,columnspan=2,sticky=tk.W+tk.E)

        self.buttoncell1 = tk.Frame(self)
        self.buttoncell1.grid(column=0, row=2, columnspan = 2, padx=10, pady=10, sticky=tk.W+tk.E)
        
        ttk.Button(self.buttoncell1, text="Add to list", command=self.add_device   ).grid(column=0, row=0, padx=7, pady=5, sticky=tk.W)
        ttk.Button(self.buttoncell1, text="Remove"     , command=self.remove_device).grid(column=1, row=0, padx=7, pady=5)
        ttk.Button(self.buttoncell1, text="Load config", command=self.load_config  ).grid(column=2, row=0, padx=7, pady=5)
        ttk.Button(self.buttoncell1, text="Save config", command=self.save_config  ).grid(column=3, row=0, padx=7, pady=5, sticky=tk.E)

        self.buttoncell1.grid_columnconfigure(0,weight=1)
        self.buttoncell1.grid_columnconfigure(1,weight=1)
        self.buttoncell1.grid_columnconfigure(2,weight=1)
        self.buttoncell1.grid_columnconfigure(3,weight=1)
        
        self.enddate = datetime.now()
        self.startdate = self.enddate - timedelta(days=1)
        self.args_dict = {'debug':False, 'starttime':'', 'stoptime':'', 'outdir':'', 'paramlist':[]}
        self.df = None
        
        self.startcell=tk.Frame(self)
        self.startcell.grid(column=0,row=3,columnspan=2, padx=10, pady=10, sticky=tk.W + tk.E)
        
        self.startdatelabel=tk.Label(self.startcell,text="Start:")
        self.startdatelabel.grid(column=0,row=0, padx=5, pady=5, sticky=tk.W)

        self.startdatecal = DateEntry(self.startcell,width=11,bg='white',fg='black',borderwidth=2)
        self.startdatecal.set_date(self.startdate)
        self.startdatecal.grid(column=1,row=0, padx=5, pady=5)        
        self.startdatecal.bind("<<DateEntrySelected>>", self.update_startdate)

        self.starth_spin = ttk.Spinbox(self.startcell, from_=0,to=23, width=4, wrap=True, command=self.update_starttime)
        self.starth_spin.grid(column=2,row=0, padx=5, pady=5, sticky=tk.E)
        self.starth_spin.set(self.startdate.hour)
        self.startm_spin = ttk.Spinbox(self.startcell, from_=0,to=59, width=4, wrap=True, command=self.update_starttime)
        self.startm_spin.grid(column=3,row=0, padx=5, pady=5, sticky=tk.W)
        self.startm_spin.set(self.startdate.minute)

        self.intvar = tk.StringVar()
        interval_opts = ['seconds=1','minutes=1','hours=1','days=1','weeks=1','months=1']
        self.interval = ttk.Combobox(self.startcell, textvar=self.intvar, values=interval_opts, width=10,justify='center')
        self.interval.option_add('*TCombobox*Listbox.Justify', 'center')
        self.interval.set('Interval')
        self.intvar.trace('w',self.set_start_interval)
        #self.interval.bind('<<ComboboxSelected>>',self.set_start_interval)        
        self.interval.grid(column=4, row=0, padx=5, sticky=tk.W)
        self.startcell.grid_columnconfigure(0,weight=1)
        self.startcell.grid_columnconfigure(1,weight=1)
        self.startcell.grid_columnconfigure(2,weight=1)
        self.startcell.grid_columnconfigure(3,weight=1)
        
        self.endcell=tk.Frame(self)
        self.endcell.grid(column=0,row=4, columnspan=2, padx=10, pady=10, sticky=tk.W + tk.E)

        self.enddatelabel=tk.Label(self.endcell,text="  End:")
        self.enddatelabel.grid(column=0,row=0, padx=5, pady=5, sticky=tk.W)
         
        self.enddatecal = DateEntry(self.endcell,width=11,bg='white',fg='black',borderwidth=2)
        self.enddatecal.set_date(self.enddate)
        self.enddatecal.grid(column=1,row=0, padx=5, pady=5)
        self.enddatecal.bind("<<DateEntrySelected>>", self.update_enddate)

        self.endh_spin = ttk.Spinbox(self.endcell, from_=0,to=23, width=4, wrap=True, command=self.update_endtime)
        self.endh_spin.grid(column=2,row=0, padx=5, pady=5,sticky=tk.E)
        self.endh_spin.set(self.enddate.hour)
        self.endm_spin = ttk.Spinbox(self.endcell, from_=0,to=59, width=4,wrap=True, command=self.update_endtime)
        self.endm_spin.grid(column=3,row=0, padx=5, pady=5,sticky=tk.W)
        self.endm_spin.set(self.enddate.minute)

        ttk.Button(self.endcell, text="Now", command=self.set_end_now, width=8).grid(column=4, row=0, padx=5, pady=5,sticky=tk.E)
        self.endcell.grid_columnconfigure(0,weight=1)
        self.endcell.grid_columnconfigure(1,weight=1)
        self.endcell.grid_columnconfigure(2,weight=1)
        self.endcell.grid_columnconfigure(3,weight=1)
        
        self.buttoncell2 = tk.Frame(self)
        self.buttoncell2.grid(column=0, row=5, columnspan = 2, padx=10, pady=10, sticky=tk.W + tk.E)

        ttk.Button(self.buttoncell2, text="Get data"    , command=self.get_data      ).grid(column=0, row=0, padx=7, pady=5, sticky=tk.W)
        ttk.Button(self.buttoncell2, text="Plot data"    , command=self.plot_data    ).grid(column=1, row=0, padx=7, pady=5)
        ttk.Button(self.buttoncell2, text="Advanced plot", command=self.advanced_plot).grid(column=2, row=0, padx=7, pady=5)
        ttk.Button(self.buttoncell2, text="Save to file" , command=self.save_to_file ).grid(column=3, row=0, padx=7, pady=5, sticky=tk.E)
        ttk.Button(self.buttoncell2, text="Quit", command=container.destroy).grid(column=3, row=2, padx=7, pady=10,sticky=tk.E)
        
        self.buttoncell2.grid_columnconfigure(0,weight=1)
        self.buttoncell2.grid_columnconfigure(1,weight=1)
        self.buttoncell2.grid_columnconfigure(2,weight=1)
        self.buttoncell2.grid_columnconfigure(3,weight=1)
        
        self.grid(padx=10, pady=10, sticky=tk.NSEW)

    '''
    def fill_device(self,event):
        if event.keysym in ["BackSpace","Left","Right","Shift_L","Shift_R","Tab"]:
            return

        devtxt=self.device.get()[:self.device.index(tk.INSERT)]
        l=len(devtxt)
        devs=[e[0] for e in self.cfg.get_list_of_devices(all=True) if e[0].find(devtxt.upper())==0]

        currindex=devs.index(self.currdevice) if hasattr(self,"currdevice") and self.currdevice in devs else 0

        if event.keysym=="Up" and currindex>0:
            currindex-=1
        if event.keysym=="Down" and currindex<len(devs)-1:
            currindex+=1

        self.currdevice=devs[currindex] if len(devs)>0 else ""
        self.device.delete(0,tk.END)
        self.device.insert(0,devtxt+self.currdevice[l:])
        self.device.icursor(l)
        self.device.select_range(l,tk.END)
    '''
    def fill_device(self,event):
        if event.keysym in ["BackSpace","Left","Right","Shift_L","Shift_R","Tab"]:
            return
        
        alldevlist=[]
        if self.device.get()[0].upper() in self.acnet_devs:
            alldevlist=self.acnet_devs[self.device.get()[0].upper()]
        else:
            alldevlist=data_grabber.find_devices(self.device.get()[0].upper())
            self.acnet_devs[self.device.get()[0].upper()]=alldevlist
        
        devtxt=self.device.get()[:self.device.index(tk.INSERT)]
        l=len(devtxt)
        self.device['values']=[e for e in alldevlist if e.find(devtxt.upper())==0]
        if len(self.device['values'])==0:
            return
        self.device.delete(0,tk.END)
        self.device.insert(0,devtxt+self.device['values'][0][l:])
        self.device.icursor(l)
        self.device.select_range(l,tk.END)     
    
    def fill_node_event(self,event):
        self.device.set(self.device.get().upper())
        self.node['values']=['%s %s'%(n,e) for (n,e) in data_grabber.find_nodes(self.device.get())]
        if len(self.node['values'])==0:
            return
        self.node.set(self.node['values'][0])
        self.node.select_range(0,tk.END)
        self.node.icursor(tk.END)
        
    def add_device(self):
        if "DEVICE" in self.device.get().upper():
            return
        self.devlist.insert(parent='',index='end',text='',
                       values=(self.device.get().upper(),self.node.get().split()[0],self.node.get().split()[1]))
        self.cfg.update_device(device=self.device.get().upper(),node=self.node.get().split()[0],event=self.node.get().split()[1],active=True)
        
    def remove_device(self):
        selected_devs = self.devlist.selection()        
        for dev in selected_devs:
            self.cfg.update_device(device=self.devlist.item(dev)["values"][0],active=False)
            self.devlist.delete(dev)
            
    def load_config(self):
        filename=fd.askopenfilename(initialdir = os.getcwd(), filetypes = [('','*.json')])
        if filename=="":
            return
        self.cfg.load_config(filename)
        for item in self.devlist.get_children():
            self.devlist.delete(item)
        for val in self.cfg.get_list_of_devices():
            self.devlist.insert(parent='',index='end',text='',values=val)

    def save_config(self):
        filename=fd.asksaveasfilename(defaultextension=".json",initialdir = os.getcwd(), filetypes = [('','*.json')])
        if filename=="":
            return
        self.cfg.save_config(filename)

    def get_data(self):
        print("Start",self.startdate.isoformat(timespec='seconds'))
        print("End",self.enddate.isoformat(timespec='seconds'))

        if self.startdate >= self.enddate:
            print('Select Start time earlier than End time')
            return
        
        self.args_dict['starttime'] = '{0:%Y-%m-%d+%H:%M:%S}'.format(self.startdate)
        self.args_dict['stoptime'] = '{0:%Y-%m-%d+%H:%M:%S}'.format(self.enddate)
        self.args_dict['paramlist']=[]
        for line in self.devlist.get_children():
            self.args_dict['paramlist'].append(self.devlist.item(line)['values'])
            
        self.args_dict['debug'] = True
    
        # fetch data
        status,self.df = data_grabber.fetch_data(self.args_dict)
        for st in status:
            if st:
                showwarning('Warning','%s'%st)
        
    def plot_data(self):
        plotWin = PlotDialog(self)

    def advanced_plot(self):
        plotWin = AdvancedPlotDialog(self)

    def save_to_file(self):
        filename = fd.asksaveasfilename(initialdir=os.getcwd(),filetypes=[('Comma-separated text','*.csv')])
        try:
            data_grabber.save_to_file(self.args_dict,self.df,filename)
        except ValueError as error:
            showerror(title='Error',message=error)

    def update_startdate(self,event):
        self.startdate = self.startdate.replace(year=self.startdatecal.get_date().year, month=self.startdatecal.get_date().month, day=self.startdatecal.get_date().day)

    def update_enddate(self,event):
        self.enddate = self.enddate.replace(year=self.enddatecal.get_date().year, month=self.enddatecal.get_date().month, day=self.enddatecal.get_date().day)

    def update_starttime(self):
        self.startdate = self.startdate.replace(hour=int(self.starth_spin.get()),minute=int(self.startm_spin.get()))

    def update_endtime(self):
        self.enddate = self.enddate.replace(hour=int(self.endh_spin.get()),minute=int(self.endm_spin.get()))

    def set_end_now(self):
        self.enddate = datetime.now()
        self.enddatecal.set_date(self.enddate)
        self.endh_spin.set(self.enddate.hour)
        self.endm_spin.set(self.enddate.minute)

    def set_start_interval(self,*args):
        match=re.findall(r'(seconds|minutes|hours|days|weeks|months)=(\d+)',self.interval.get())
        if match:
            self.startdate=self.enddate-timedelta(**{x:int(y) for (x,y) in match})
            
        self.startdatecal.set_date(self.startdate)
        self.starth_spin.set(self.startdate.hour)
        self.startm_spin.set(self.startdate.minute)

class AdvancedPlotDialog(tk.Toplevel, object):
    def __init__(self,parent):
        super().__init__(parent)
        self.title("Advanced plot")
        self.parent=parent
        plt.rcParams["axes.titlelocation"] = 'right'
        plt.style.use('dark_background')
        overlap = {name for name in mcolors.CSS4_COLORS
                if f'xkcd:{name}' in mcolors.XKCD_COLORS}

        overlap.difference_update(['aqua','black','white','lime','chocolate','gold'])
        self.colors = [mcolors.XKCD_COLORS[f'xkcd:{color_name}'].upper() for color_name in sorted(overlap)]
        self.colornames = sorted(overlap)
        
        self.vars=[key for key in list(parent.df.keys()) if key.find('tstamp')==-1]        
        self.ldf=parent.df.copy(deep=True) #copy dataframe before aligning timestamps/renaming columns

        dflist=[]
        dfdev={}
        for dev in self.vars:
            dfdev=self.ldf[['tstamp_%s'%dev,dev]]
            dfdev.rename(columns={'tstamp_%s'%dev:'time'},inplace=True)
            #dfdev['tstamp']= pd.to_datetime(dfdev['tstamp'])
            dflist.append(dfdev.dropna())

        df_merged = reduce(lambda  left,right: pd.merge_asof(left,right,on=['time'],direction='nearest',tolerance=20), dflist).dropna() #fillna('nodata')

        self.vars.insert(0,'time')
        self.ldf=df_merged.rename({key : key.replace(':','')  for key in self.ldf.keys()},axis=1) #eval does not like :
        print(self.ldf)
        
        self.plotdef=tk.Toplevel(parent)
        self.plotdef.title("Advanced plot")
        alist_scroll=tk.Scrollbar(self.plotdef)
        self.alist=ttk.Treeview(self.plotdef,yscrollcommand=alist_scroll.set)
        alist_scroll.config(command=self.alist.yview)
        alist_scroll.grid(column=1,row=0,sticky=tk.N+tk.S,padx=(0,10),pady=10)
        self.alist['columns']=('device')
        self.alist.column("#0",width=0,stretch=tk.NO)
        self.alist.column("device",anchor=tk.W,width=160)
        self.alist.heading("#0",text="",anchor=tk.CENTER)
        self.alist.heading("device",text="Y axis",anchor=tk.CENTER)
        self.alist.grid(column=0,row=0,columnspan=3,sticky = tk.NSEW,padx=(10,0),pady=10)

        tk.Label(self.plotdef,text="X axis:").grid(column=0,row=1,padx=10)
        self.xaxis=ttk.Combobox(self.plotdef,width=16)
        self.xaxis['values']=self.vars
        self.xaxis.set(self.xaxis['values'][0])
        self.xaxis.grid(column=1,row=1,columnspan=2,padx=10,pady=10)

        self.yaxis=ttk.Combobox(self.plotdef,width=24)
        self.yaxis.insert(0,'Y axis')
        self.yaxis.grid(column=0,row=2,padx=10,pady=10)
        self.yaxis.bind("<KeyRelease>",self.fill_yaxis)
        self.yaxis.bind("<Tab>",self.fill_yaxis)
        self.yaxis.bind("<FocusIn>",lambda x: self.yaxis.selection_range(0, tk.END))
        
        tk.Button(self.plotdef,text="Add", command=self.add_device).grid(column=1, row=2, padx=10, pady=10)
        tk.Button(self.plotdef,text="Remove", command=self.remove_device).grid(column=2, row=2, padx=10, pady=10)
        tk.Button(self.plotdef,text="Update plot", command=self.update_plot).grid(column=1, row=3, padx=7, pady=5)
        tk.Button(self.plotdef,text="Close", command=self.close).grid(column=2, row=3, padx=7, pady=5)

        self.plotdef.update()
        #self.plotdef.grid(padx=10, pady=10, sticky=tk.NSEW)
        
        self.fig = Figure(figsize=(10,10))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.draw()
        self.toolbar = MyToolbar(self.canvas,self)
        self.toolbar.update()
        self.canvas.get_tk_widget().grid(column=0, row=0, sticky=tk.NSEW )
        self.toolbar.grid(column=0, row=1, columnspan=3, sticky = tk.W + tk.E)
        
        print(self.plotdef.winfo_x()+self.plotdef.winfo_width())
        print(self.plotdef.winfo_y())
        self.wm_geometry("+%d+%d" % (self.plotdef.winfo_x()+self.plotdef.winfo_width(), self.plotdef.winfo_y()))

    def fill_yaxis(self,event):
        if event.keysym=="Tab" and self.yaxis.selection_present(): 
            self.yaxis.icursor(tk.END)
            self.yaxis.select_range(tk.END,tk.END)     
            return "break"
        if event.keysym in ["BackSpace","Left","Right","Shift_L","Shift_R","Tab"]:
            return
        
        alldevlist=self.vars
        ops = [index.start() for index in re.finditer('\+|\-|\/|\*| ',self.yaxis.get())]
        first=0 if len(ops)==0 else ops[-1]+1
        devtxt=self.yaxis.get()[first:self.yaxis.index(tk.INSERT)]
        l=len(devtxt)
        self.yaxis['values']=[self.yaxis.get()[0:first]+e for e in alldevlist if e.find(devtxt.upper())==0]
        if len(self.yaxis['values'])==0 or l==0:
            return
        self.yaxis.delete(first,tk.END)
        self.yaxis.insert(first,devtxt+self.yaxis['values'][0][first+l:])
        self.yaxis.icursor(first+l)
        self.yaxis.select_range(first+l,tk.END)     
    
    def update_plot(self):
        self.fig.clf()
        ylist=[self.alist.item(line)['values'][0] for line in self.alist.get_children()]
        self.ax = [None]*len(ylist)
        self.ax[0] = self.fig.add_subplot(111)
        self.ax[0].xaxis.grid(True, which='major')
        self.ax[0].yaxis.grid(True, which='major')
        self.ax[0].set_xlabel(self.xaxis.get())
        for i in range(1,len(ylist)):
            self.ax[i] = self.ax[0].twinx()
        for i,yd in enumerate(ylist):
            space= space + '  '*(len(yd)+1) if i>0 else ''
            col=self.colors[i]
            self.ax[i].set_title(yd+space,color=col,ha='right',fontsize='large')                                
            self.ax[i].tick_params(axis='y', colors=col, labelsize='large',rotation=90)
            ydata=self.ldf.eval(yd.replace(":",""))
            xx=self.ldf['time'].apply(lambda x: datetime.fromtimestamp(x) if x==x else x) if "time" in self.xaxis.get() else self.ldf[self.xaxis.get().replace(":","")]
            self.ax[i].plot(xx,ydata,c=col,marker='.',linestyle='None')
            self.ax[i].yaxis.set_major_locator(mt.LinearLocator(5))

            if i%2==0:
                self.ax[i].yaxis.tick_left()
                for yl in self.ax[i].get_yticklabels():
                    yl.set_x( -0.025*(i/2.) )
                    yl.set(verticalalignment='bottom')
                    
            else:
                self.ax[i].yaxis.tick_right()
                for yl in self.ax[i].get_yticklabels():
                    yl.set_x( 1.0+0.025*(i-1)/2.)
                    yl.set(verticalalignment='bottom')
                    
        self.canvas.draw()
        
            
    def close(self):
        self.destroy()
        self.plotdef.destroy()
        
    def add_device(self):
        if "AXIS" in self.yaxis.get().upper():
            return
        self.alist.insert(parent='',index='end',text='',
                       values=(self.yaxis.get().upper(),))
        
    def remove_device(self):
        selected_devs = self.alist.selection()        
        for dev in selected_devs:
            self.alist.delete(dev)
        
class PlotDialog(tk.Toplevel, object):
    def __init__(self,parent):
        super().__init__(parent)
        self.title("Data")
        self.parent=parent

        plt.rcParams["axes.titlelocation"] = 'right'
        plt.style.use('dark_background')
        overlap = {name for name in mcolors.CSS4_COLORS
                   if f'xkcd:{name}' in mcolors.XKCD_COLORS}

        overlap.difference_update(['aqua','black','white','lime','chocolate','gold'])
        self.colors = [mcolors.XKCD_COLORS[f'xkcd:{color_name}'].upper() for color_name in sorted(overlap)]
        self.colornames = sorted(overlap)
        
        ts = [key for key in list(parent.df.keys()) if key.find('tstamp')!=-1]
        data = [key for key in list(parent.df.keys()) if key.find('tstamp')==-1]
        
        self.fig = Figure(figsize=(8,8)) # i like squares
        self.ax = [None]*len(data)
        self.ax[0] = self.fig.add_subplot(111)
        self.ax[0].xaxis.grid(True, which='major')
        self.ax[0].yaxis.grid(True, which='major')
        for i in range(1,len(data)):
            self.ax[i] = self.ax[0].twinx()
        self.ax[0].set_xlabel("time")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.draw()        
        #self.toolbar = NavigationToolbar2Tk(self.canvas, self, pack_toolbar=False)
        self.toolbar = MyToolbar(self.canvas,self)
        self.toolbar.update()
        self.canvas.get_tk_widget().grid(column=0, row=0, sticky=tk.NSEW )
        self.toolbar.grid(column=0, row=1, columnspan=3, sticky = tk.W + tk.E)
        
        for i,(t,d) in enumerate(zip(ts,data)):
            space= space + '  '*(len(d)+1) if i>0 else ''
            col=parent.cfg.get_style(d,"line_color") if parent.cfg.get_style(d,"line_color") is not None else self.colors[i]
            self.ax[i].set_title(d+space,color=col,ha='right',fontsize='large')                                
            self.ax[i].tick_params(axis='y', colors=col, labelsize='large',rotation=90)
            tstamps=parent.df[t].apply(lambda x: datetime.fromtimestamp(x) if x==x else x)
            self.ax[i].plot(tstamps,parent.df[d],c=col,label=d)
            self.ax[i].yaxis.set_major_locator(mt.LinearLocator(5))
            
            if i%2==0:
                self.ax[i].yaxis.tick_left()
                for yl in self.ax[i].get_yticklabels():
                    yl.set_x( -0.025*(i/2.) )
                    yl.set(verticalalignment='bottom')
                    
            else:
                self.ax[i].yaxis.tick_right()
                for yl in self.ax[i].get_yticklabels():
                    yl.set_x( 1.0+0.025*(i-1)/2.)
                    yl.set(verticalalignment='bottom')
                                        
        self.fig.subplots_adjust(left=0.12)
        self.fig.subplots_adjust(right=0.88)
        self.fig.subplots_adjust(bottom=0.12)
        self.fig.subplots_adjust(top=0.88)

        self.canvas.draw()
        
class MyToolbar(NavigationToolbar2Tk):
  def __init__(self, figure_canvas, window):
      self.window=window
      self.toolitems = [*NavigationToolbar2Tk.toolitems]
      self.toolitems.insert(
          [name for name, *_ in self.toolitems].index("Subplots") + 1,
          ("Customize", "Edit axis, curve and image parameters",'qt4_editor_options','edit_parameters'))

      NavigationToolbar2Tk.__init__(self, figure_canvas,window, pack_toolbar=False)

  def edit_parameters(self):
    self.edit = EditDialog(self)
        

  def apply_style(self):
      axes = self.window.ax
      item = self.edit.axselect.get()
      if axes and len(self.edit.titles)>0 and item!='':
          ax = axes[self.edit.titles.index(item)]
          if self.edit.colselect.get() !='':
              ax.get_lines()[0].set_color(self.edit.colselect.get())
              ax.tick_params(colors=self.edit.colselect.get(), which='both',axis='y')
              ax.set_title(ax.get_title('right'),color=self.edit.colselect.get(),ha='right',fontsize='large')
              self.window.parent.cfg.update_device(device=item,line_color=self.edit.colselect.get())
          if self.edit.lineselect.get() !='':
              ax.get_lines()[0].set_linestyle(self.edit.lineselect.get())
              self.window.parent.cfg.update_device(device=item,line_style=self.edit.lineselect.get())
          if self.edit.markerselect.get() !='':
              ax.get_lines()[0].set_marker(self.edit.markerselect.get())
              self.window.parent.cfg.update_device(device=item,marker_style=self.edit.markerselect.get())

          ymin = self.edit.yminselect.get()
          ymax = self.edit.ymaxselect.get()
          if ymin != '' and ymax !='' and float(ymax)>float(ymin):
              ax.set_ylim(float(ymin),float(ymax))
        
          self.canvas.draw()

class EditDialog(tk.Toplevel, object):
    def __init__(self,parent):
        super().__init__(parent)
        self.title("Edit properties")
        #self.geometry("200x200")

        axes = parent.window.ax
        self.titles = []
        if not axes:
            showwarning('Warning','There are no axes to edit')
            
        else:
            self.titles = [
                ax.get_label().strip() or
                ax.get_title().strip() or
                ax.get_title('left').strip() or
                ax.get_title('right').strip() or
                " - ".join(filter(None, [ax.get_xlabel(), ax.get_ylabel()])) or
                f"<anonymous {type(ax).__name__}>"
                for ax in axes]

        
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.editframe = tk.Frame(self)
        self.editframe.grid(column=0,row=0, sticky=tk.NSEW, padx=10, pady=10)

        self.axlabel = tk.Label(self.editframe,text='Select axis:')
        self.axlabel.grid(column=0, row=0)
        self.axselect = ttk.Combobox(self.editframe, values=self.titles, width=10,justify='left')
        self.axselect.option_add('*TCombobox*Listbox.Justify', 'center')
        self.axselect.grid(column=1,row=0)
        self.collabel = tk.Label(self.editframe, text='Color:')
        self.collabel.grid(column=0,row=1)
        self.colselect = ttk.Combobox(self.editframe, values = parent.window.colornames, width=10, justify='left' )
        self.colselect.option_add('*TCombobox*Listbox.Justify', 'center')
        self.colselect.grid(column=1,row=1)
        self.yminlabel = tk.Label(self.editframe, text='Y min:')
        self.yminlabel.grid(column=0,row=2)
        self.yminselect=tk.Entry(self.editframe,width=10)
        self.yminselect.insert(0,'0.0')
        self.yminselect.bind("<FocusIn>",lambda x: self.yminselect.selection_range(0, tk.END))    
        self.yminselect.grid(column=1,row=2)
        self.ymaxlabel = tk.Label(self.editframe, text='Y max:')
        self.ymaxlabel.grid(column=0,row=3)
        self.ymaxselect=tk.Entry(self.editframe,width=10)
        self.ymaxselect.insert(0,'0.0')
        self.ymaxselect.bind("<FocusIn>",lambda x: self.ymaxselect.selection_range(0, tk.END))    
        self.ymaxselect.grid(column=1,row=3)
        self.linelabel = tk.Label(self.editframe,text='Line style:')
        self.linelabel.grid(column=0,row=4)
        self.lineselect = ttk.Combobox(self.editframe, values = ['solid','dashed','dashdot','dotted','none'], width=10, justify='left' )
        self.lineselect.grid(column=1,row=4)
        self.markerlabel = tk.Label(self.editframe,text='Marker style:')
        self.markerlabel.grid(column=0,row=5)
        self.markerselect = ttk.Combobox(self.editframe, values = ['','.','x','o','^','v','<','>','*','s','p','h','+','P','d','D'], width=10, justify='left' )
        self.markerselect.grid(column=1,row=5)

        ttk.Button(self.editframe, text="Apply style", command=parent.apply_style).grid(column=0, row=6)
        ttk.Button(self.editframe, text="Close", command=self.destroy).grid(column=1, row=6)

    
class DataGrabber(tk.Tk):
    def __init__(self):
        super().__init__()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        self.title('D44 Lite')
        #self.geometry('500x500')
        self.resizable(True,True)


if __name__ =="__main__":
        app = DataGrabber()
        MainFrame(app)
        app.mainloop()

