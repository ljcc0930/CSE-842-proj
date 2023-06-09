import os
import shutil

import torch as th
from torch.optim import lr_scheduler
import torch.utils.data as Data

import unlearn
import trainer
import arg_parser

from model import BertClassifier
import utils
import evaluation


def main():
    args = arg_parser.parse_args()

    max_length = args.max_length
    batch_size = args.batch_size
    nb_epochs = args.nb_epochs
    bert_lr = args.bert_lr
    dataset = args.dataset
    bert_init = args.bert_init
    checkpoint_dir = args.checkpoint_dir
    forget_ratio = args.forget_ratio
    unlearn_method = args.unlearn_method

    adj, features, y_train, y_val, y_test, train_mask, val_mask, test_mask, train_size, test_size = utils.load_corpus(
        dataset)

    nb_node = adj.shape[0]
    nb_train, nb_val, nb_test = train_mask.sum(), val_mask.sum(), test_mask.sum()
    nb_forget = int(nb_train * forget_ratio)
    nb_retain = nb_train - nb_forget
    nb_class = y_train.shape[1]
    args.num_classes = nb_class

    model = BertClassifier(pretrained_model=bert_init,
                           nb_class=nb_class).cuda()

    y = th.LongTensor((y_train + y_val + y_test).argmax(axis=1))

    corpus_file = './data/corpus/'+dataset+'_shuffle.txt'
    with open(corpus_file, 'r') as f:
        text = f.read()
        text = text.replace('\\', '')
        text = text.split('\n')

    def encode_input(text, tokenizer):
        input = tokenizer(text, max_length=max_length,
                          truncation=True, padding=True, return_tensors='pt')
        return input.input_ids, input.attention_mask

    input_ids, attention_mask = {}, {}
    label = {}

    input_ids_, attention_mask_ = encode_input(text, model.tokenizer)

    # create train/test/val datasets and dataloaders
    curr = 0
    for split, num in zip(['retain', 'forget', 'val'], [nb_retain, nb_forget, nb_val]):
        input_ids[split] = input_ids_[curr: curr + num]
        attention_mask[split] = attention_mask_[curr: curr + num]
        label[split] = y[curr: curr + num]
        curr += num

    label['test'] = y[-nb_test:]
    input_ids['test'] = input_ids_[-nb_test:]
    attention_mask['test'] = attention_mask_[-nb_test:]

    datasets = {}
    loader = {}
    for split in ['retain', 'forget', 'val', 'test']:
        datasets[split] = Data.TensorDataset(
            input_ids[split], attention_mask[split], label[split])
        loader[split] = Data.DataLoader(
            datasets[split], batch_size=batch_size, shuffle=True)

    criterion = th.nn.CrossEntropyLoss()

    unlearn_result = unlearn.load_unlearn_checkpoint(model, args)

    evaluation_result = None

    if unlearn_result is None or args.rerun:
        unlearn_func = unlearn.get_unlearn_method(unlearn_method)
        if unlearn_method != "retrain":
            checkpoint = f"checkpoint/{bert_init}_{dataset}/checkpoint.pth"
            checkpoint_dict = th.load(checkpoint)
            model.bert_model.load_state_dict(checkpoint_dict['bert_model'])
            model.classifier.load_state_dict(checkpoint_dict['classifier'])

        # optimizer = th.optim.Adam(model.parameters(), lr=bert_lr)
        # scheduler = lr_scheduler.MultiStepLR(optimizer, milestones=[30], gamma=0.1)

        unlearn_func(loader, model, criterion, args)
        unlearn.save_unlearn_checkpoint(model, None, args)
    else:
        model, evaluation_result = unlearn_result

    if evaluation_result is None:
        evaluation_result = {}
    if "TA" not in evaluation_result:
        evaluation_result["TA"] = trainer.validate(
            loader['test'], model, criterion, args)
        unlearn.save_unlearn_checkpoint(model, evaluation_result, args)
    if "UA" not in evaluation_result:
        evaluation_result["UA"] = 1 - \
            trainer.validate(loader['forget'], model, criterion, args)
        unlearn.save_unlearn_checkpoint(model, evaluation_result, args)
    if "RA" not in evaluation_result:
        evaluation_result["RA"] = trainer.validate(
            loader['retain'], model, criterion, args)
        unlearn.save_unlearn_checkpoint(model, evaluation_result, args)
    
    if 'MIA' not in evaluation_result:
        test_len = min(len(datasets['test']), len(datasets['retain']))

        shadow_train = Data.Subset(
            datasets['retain'], list(range(test_len)))
        shadow_test = Data.Subset(
            datasets['test'], list(range(test_len)))
        shadow_train_loader = Data.DataLoader(
            shadow_train, batch_size=args.batch_size, shuffle=False)
        shadow_test_loader = Data.DataLoader(
            shadow_test, batch_size=args.batch_size, shuffle=False)

        evaluation_result['MIA'] = evaluation.SVC_MIA(
            shadow_train=shadow_train_loader, shadow_test=shadow_test_loader,
            target_train=None, target_test=loader['forget'],
            model=model)
        unlearn.save_unlearn_checkpoint(model, evaluation_result, args)

    unlearn.save_unlearn_checkpoint(model, evaluation_result, args)


if __name__ == "__main__":
    main()
