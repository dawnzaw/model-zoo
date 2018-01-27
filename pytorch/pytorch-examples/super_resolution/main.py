from __future__ import print_function
import argparse
from math import log10

import torch
import torch.nn as nn
import torch.optim as optim
from torch.autograd import Variable
from torch.utils.data import DataLoader
from model import Net
from data import get_training_set, get_test_set

import missinglink

OWNER_ID = '764e5d22-7128-a8cf-4213-c49beec73998'
PROJECT_TOKEN = 'UJrhwlpluaSbrWew'
HOST = 'https://missinglink-staging.appspot.com'

missinglink_project = missinglink.PyTorchProject(owner_id=OWNER_ID, project_token=PROJECT_TOKEN, host=HOST)


# Training settings
parser = argparse.ArgumentParser(description='PyTorch Super Res Example')
parser.add_argument('--upscale_factor', type=int, required=True, help="super resolution upscale factor")
parser.add_argument('--batchSize', type=int, default=64, help='training batch size')
parser.add_argument('--testBatchSize', type=int, default=10, help='testing batch size')
parser.add_argument('--nEpochs', type=int, default=2, help='number of epochs to train for')
parser.add_argument('--lr', type=float, default=0.01, help='Learning Rate. Default=0.01')
parser.add_argument('--cuda', action='store_true', help='use cuda?')
parser.add_argument('--threads', type=int, default=4, help='number of threads for data loader to use')
parser.add_argument('--seed', type=int, default=123, help='random seed to use. Default=123')
opt = parser.parse_args()

print(opt)

cuda = opt.cuda
if cuda and not torch.cuda.is_available():
    raise Exception("No GPU found, please run without --cuda")

torch.manual_seed(opt.seed)
if cuda:
    torch.cuda.manual_seed(opt.seed)

print('===> Loading datasets')
train_set = get_training_set(opt.upscale_factor)
test_set = get_test_set(opt.upscale_factor)
training_data_loader = DataLoader(dataset=train_set, num_workers=opt.threads, batch_size=opt.batchSize, shuffle=True)
testing_data_loader = DataLoader(dataset=test_set, num_workers=opt.threads, batch_size=opt.testBatchSize, shuffle=False)

print('===> Building model')
model = Net(upscale_factor=opt.upscale_factor)
criterion = nn.MSELoss()

if cuda:
    model = model.cuda()
    criterion = criterion.cuda()

optimizer = optim.Adam(model.parameters(), lr=opt.lr)


def train(epoch):
    epoch_loss = 0
    for iteration, batch in experiment.batch_loop(iterable=training_data_loader):
        input, target = Variable(batch[0]), Variable(batch[1])
        if cuda:
            input = input.cuda()
            target = target.cuda()

        optimizer.zero_grad()
        loss = wrapped_loss(model(input), target)
        epoch_loss += loss.data[0]
        loss.backward()
        optimizer.step()

        print("===> Epoch[{}]({}/{}): Loss: {:.4f}".format(epoch, iteration, len(training_data_loader), loss.data[0]))

    print("===> Epoch {} Complete: Avg. Loss: {:.4f}".format(
        epoch, wrapped_avg_loss(epoch_loss, len(training_data_loader)))
    )


def test():
    avg_psnr = 0
    with experiment.validation():
        for batch in testing_data_loader:
            input, target = Variable(batch[0]), Variable(batch[1])
            if cuda:
                input = input.cuda()
                target = target.cuda()

            prediction = model(input)
            mse = wrapped_loss(prediction, target)
            psnr = 10 * log10(1 / mse.data[0])
            avg_psnr += psnr
        print("===> Avg. PSNR: {:.4f} dB".format(wrapped_avg_psnr(avg_psnr, len(testing_data_loader))))


def checkpoint(epoch):
    model_out_path = "model_epoch_{}.pth".format(epoch)
    torch.save(model, model_out_path)
    print("Checkpoint saved to {}".format(model_out_path))


def average(total, count):
    return total / count


with missinglink_project.create_experiment(
    model,
    display_name='Super Resolution PyTorch',
    optimizer=optimizer,
    metrics={
        'Loss': criterion,
        'Avg. Loss': average,
        'Avg. PSNR': average,
    },
) as experiment:
    wrapped_loss = experiment.metrics['Loss']
    wrapped_avg_loss = experiment.metrics['Avg. Loss']
    wrapped_avg_psnr = experiment.metrics['Avg. PSNR']

    for epoch in experiment.epoch_loop(opt.nEpochs):
        train(epoch)
        test()
        checkpoint(epoch)
