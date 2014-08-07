from argparse import ArgumentParser
import pandas
import terra
import matplotlib
matplotlib.use('Agg')

parser = ArgumentParser(description='Thin wrapper around terra module')
parser.add_argument('args',nargs='+',type=str,help='file[s] function keywords')
parser.add_argument('--multi',type=int,default=1,help='')
parser.add_argument('--P'   ,type=float,default=-1,help='Period to cut')
parser.add_argument('--t0'  ,type=float,default=-1,help='epoch to cut')
parser.add_argument('--tdur',type=float,default=-1,help='duration to cut')

parser.add_argument('--update',action='store_true',help='Set to use h5plus objects')
args  = parser.parse_args()

index = args.args[-1]
files = args.args[:-1]
multi = args.multi
    
dL = []
for f in files:
    df = pandas.read_csv(f,index_col=0)
    if len( index ) ==9:
        df.index = df.outfile.apply(lambda x : x.split('/')[-1][:-3])
        d = dict(df.ix[index])
    else:
        d = dict(df.ix[ int(index) ])

    d['update'] = args.update
    dL.append(d)

def last2(s):
    sL = s.split('/')[-2:]
    sL = tuple(sL)
    return '%s/%s' % sL 

if multi > 1:
    outfile0    = dL[0]['outfile']
    if multi > 2:
        outfile = outfile0.replace('grid','grid%i'  % (multi-1))
    else:
        outfile = outfile0

    newoutfile = outfile0.replace('grid','grid%i'  % multi)

    print "copying %s to %s" %  tuple( map(last2,[outfile,newoutfile]) )
    if args.P > 0:
        pdict = dict(P=args.P,t0=args.t0,tdur=args.tdur)
    terra.multiCopyCut( outfile , newoutfile,pdict=pdict)
    for d in dL:
        d['outfile'] = newoutfile

for d in dL:
    exec("terra.%(name)s(d)" % d)

