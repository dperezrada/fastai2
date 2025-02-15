#AUTOGENERATED! DO NOT EDIT! File to edit: dev/71_callback.tensorboard.ipynb (unless otherwise specified).

__all__ = ['TensorBoardCallback', 'tensorboard_log']

#Cell
from ..test import *
from ..basics import *

#Cell
import tensorboard
from torch.utils.tensorboard import SummaryWriter
from .fp16 import ModelToHalf

#Cell
class TensorBoardCallback(Callback):
    "Saves model topology, losses & metrics"
    def __init__(self, log_dir=None, trace_model=True, log_preds=True, n_preds=9):
        store_attr(self, 'log_dir,trace_model,log_preds,n_preds')

    def begin_fit(self):
        self.writer = SummaryWriter(log_dir=self.log_dir)
        if self.trace_model:
            if hasattr(self.learn, 'mixed_precision'):
                raise Exception("Can't trace model in mixed precision, pass `trace_model=False` or don't use FP16.")
            b = self.dbunch.one_batch()
            self.learn._split(b)
            self.writer.add_graph(self.model, *self.xb)

    def after_batch(self):
        self.writer.add_scalar('train_loss', self.smooth_loss, self.train_iter)
        for i,h in enumerate(self.opt.hypers):
            for k,v in h.items(): self.writer.add_scalar(f'{k}_{i}', v, self.train_iter)

    def after_epoch(self):
        for n,v in zip(self.recorder.metric_names[2:-1], self.recorder.log[2:-1]):
            self.writer.add_scalar(n, v, self.train_iter)
        if self.log_preds:
            b = self.dbunch.valid_dl.one_batch()
            self.learn.one_batch(0, b)
            preds = getattr(self.loss_func, 'activation', noop)(self.pred)
            out = getattr(self.loss_func, 'decodes', noop)(preds)
            x,y,its,outs = self.dbunch.valid_dl.show_results(b, out, show=False, max_n=self.n_preds)
            tensorboard_log(x, y, its, outs, self.writer, self.train_iter)

    def after_fit(self): self.writer.close()

#Cell
from ..vision.data import *

#Cell
@typedispatch
def tensorboard_log(x:TensorImage, y: TensorCategory, samples, outs, writer, step):
    fig,axs = get_grid(len(samples), add_vert=1, return_fig=True)
    for i in range(2):
        axs = [b.show(ctx=c) for b,c in zip(samples.itemgot(i),axs)]
    axs = [r.show(ctx=c, color='green' if b==r else 'red')
            for b,r,c in zip(samples.itemgot(1),outs.itemgot(0),axs)]
    writer.add_figure('Sample results', fig, step)

#Cell
from ..vision.core import TensorPoint,TensorBBox
@typedispatch
def tensorboard_log(x:TensorImage, y: (TensorImageBase, TensorPoint, TensorBBox), samples, outs, writer, step):
    fig,axs = get_grid(len(samples), add_vert=1, return_fig=True, double=True)
    for i in range(2):
        axs[::2] = [b.show(ctx=c) for b,c in zip(samples.itemgot(i),axs[::2])]
    for x in [samples,outs]:
        axs[1::2] = [b.show(ctx=c) for b,c in zip(x.itemgot(0),axs[1::2])]
    writer.add_figure('Sample results', fig, step)