#!/usr/bin/env python 
from flask import Flask, render_template, request, url_for
import psycopg2
import sqlite3
import os.path
import pandas as pd
from cStringIO import StringIO as sio
import copy

host = os.environ['K2WEBAPP_HOST']
app = Flask(__name__)

tps_basedir0 = '/project/projectdirs/m1669/www/K2/TPS/C0_11-12/'
phot_basedir0 = '/project/projectdirs/m1669/www/K2/photometry/C0_11-12/'

phot_plots = """\
width ext
33% .ff-frame.png 
50% .ff.png 
33% _xy.png 
50% _gp_time_xy.png
"""
phot_plots = pd.read_table(sio(phot_plots),sep='\s')
def phot_imagepars(starname):
    """
    Return image parameters given the starname
    """
    phot_basedir = copy.copy(phot_basedir0)
    phot_basedir = phot_basedir.replace(
        "/project/projectdirs/m1669/www/",
        "http://portal.nersc.gov/project/m1669/")                         
    phot_basename = os.path.join(phot_basedir,'output',starname)

    phot_plots['url'] = phot_basename + phot_plots['ext']
    imagepars = list(phot_plots['url width'.split()].itertuples(index=False))
    return imagepars

@app.route('/photometry/<starname>')
def display_photometry(starname):
    imagepars = phot_imagepars(starname)
    templateVars = { 
        "imagepars":imagepars,
                 }
    return render_template('photometry_template.html',**templateVars)

tps_plots = """\
width ext
100% .grid.pk.png
50% .grid.lc.png
"""
tps_plots = pd.read_table(sio(tps_plots),sep='\s')

def tps_imagepars(starname):
    """
    Return image parameters given the starname
    """
    tps_basedir = copy.copy(tps_basedir0)

    
    tps_basedir = tps_basedir.replace(
        "/project/projectdirs/m1669/www/",
        "http://portal.nersc.gov/project/m1669/")                         

    print tps_basedir
    tps_basedir = os.path.join(tps_basedir,'output/%s/%s' % (starname,starname))

    tps_plots['url'] = tps_basedir + tps_plots['ext']
    imagepars = list(tps_plots['url width'.split()].itertuples(index=False))
    print imagepars
    return imagepars

@app.route('/vetting/<starname>')
def display_vetting(starname):
    dbpath = os.path.join(tps_basedir0,'scrape.db')
    print "connecting to database %s" % dbpath 
    con = sqlite3.connect(dbpath)
    cursor = con.cursor()
    df = pd.read_sql("select * from candidate where starname=%s" % starname,con)
    con.close()

    if len(df)==0:
        return "Star %s not in %s" % (starname,tps_basedir0)

    print df
    table = dict(df['P t0 tdur s2n grass num_trans'.split()].iloc[0])
    tablelong = dict(df.iloc[0])
    table['Depth [ppt]'] = 1e3*tablelong['mean']

    templateVars = { 
        "tps_imagepars":tps_imagepars(starname),
        "phot_imagepars":phot_imagepars(starname),
        "table":table,
        "tablelong":tablelong
    }

    return render_template('vetting_template.html',**templateVars)

# Insert decision of real / not real into data base 
@app.route('/hello/',methods=['POST'])
def hello():
    return request.form['isreal']

if __name__=="__main__":
    app.run(host=host,port=25000,debug=True)