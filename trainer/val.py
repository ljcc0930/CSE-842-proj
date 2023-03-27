import torch
import utils


def validate(val_loader, model, criterion, args):
    """
    Run evaluation
    """
    losses = utils.AverageMeter()
    top1 = utils.AverageMeter()

    # switch to evaluate mode
    model.eval()

    for i, (inp, mask, label) in enumerate(val_loader):
        inp = inp.cuda()
        mask = mask.cuda()
        label = label.cuda()

        # compute output
        with torch.no_grad():
            output = model(inp, mask)
            loss = criterion(output, label)

        output = output.float()
        loss = loss.float()

        # measure accuracy and record loss
        prec1 = utils.accuracy(output.data, label)[0]
        losses.update(loss.item(), inp.size(0))
        top1.update(prec1.item(), inp.size(0))

        if i % args.print_freq == 0:
            print('Test: [{0}/{1}]\t'
                  'Loss {loss.val:.4f} ({loss.avg:.4f})\t'
                  'Accuracy {top1.val:.3f} ({top1.avg:.3f})'.format(
                      i, len(val_loader), loss=losses, top1=top1))

    print('valid_accuracy {top1.avg:.3f}'
          .format(top1=top1))

    return top1.avg
