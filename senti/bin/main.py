#!/usr/bin/env python

import json
import logging
import os
import sys
from contextlib import ExitStack

import numpy as np
np.random.seed(1234)
from sklearn.preprocessing import LabelBinarizer

from senti.score import *
from senti.senti_models import *
from senti.utils import BalancedSlice, FieldExtractor, RepeatSr


def main():
    sys.setrecursionlimit(5000)
    logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)
    os.chdir('data/twitter')
    with ExitStack() as stack:
        # load data
        labelled_dir = 'semeval'
        train_sr = stack.enter_context(open('{}/train.json'.format(labelled_dir)))
        train_docs = FieldExtractor(train_sr, 'text')
        train_labels = np.fromiter(FieldExtractor(train_sr, 'label'), 'int32')
        distant_srs = [stack.enter_context(open('emote_{}.txt'.format(i), encoding='utf-8')) for i in [0, 2]]
        distant_docs = BalancedSlice(distant_srs)
        distant_labels = BalancedSlice((RepeatSr(0), RepeatSr(2)))
        unsup_sr = stack.enter_context(open('unsup.txt', encoding='utf-8'))
        unsup_docs = BalancedSlice([unsup_sr])
        dev_sr = stack.enter_context(open('{}/dev.json'.format(labelled_dir)))
        dev_docs = FieldExtractor(dev_sr, 'text')
        dev_labels = FieldExtractor(dev_sr, 'label')
        test_sr = stack.enter_context(open('{}/test.json'.format(labelled_dir)))
        test_docs = FieldExtractor(test_sr, 'text')
        test_labels = FieldExtractor(test_sr, 'label')

        # train
        senti_models = SentiModels(
            unsup_docs, distant_docs, distant_labels, train_docs, train_labels, dev_docs, dev_labels, test_docs
        )
        # pipeline_name, pipeline = senti_models.fit_voting()
        # pipeline_name, pipeline = senti_models.fit_logreg()
        # pipeline_name, pipeline = senti_models.fit_word2vec_bayes()
        # pipeline_name, pipeline = senti_models.fit_svm()
        # pipeline_name, pipeline = senti_models.fit_cnn_word()
        # pipeline_name, pipeline = senti_models.fit_cnn_char()
        # pipeline_name, pipeline = senti_models.fit_cnn_word_char()
        pipeline_name, pipeline = senti_models.fit_rnn_char_cnn_word()
        # pipeline_name, pipeline = senti_models.fit_rnn_word()

        # test_data = [('dev', dev_docs, dev_labels)]
        test_data = [('dev', dev_docs, dev_labels), ('test', test_docs, test_labels)]

        # predict & write results
        classes_ = np.array([0, 1, 2])
        for name, docs, labels in test_data:
            os.makedirs('results/{}'.format(name), exist_ok=True)
            try:
                probs = pipeline.predict_proba(docs)
            except AttributeError:
                probs = LabelBinarizer().fit(classes_).transform(pipeline.predict(docs))
            with open('{}/{}.json'.format(labelled_dir, name)) as sr, \
                    open('results/{}/{}.json'.format(name, pipeline_name), 'w') as results_sr:
                for line, prob in zip(sr, probs):
                    results_sr.write(json.dumps({
                        'id': json.loads(line)['id'], 'label': int(classes_[np.argmax(prob)]),
                        'probs': [(c.item(), prob.item()) for c, prob in zip(classes_, prob)]
                    }) + '\n')
            print('{} data: '.format(name))
            labels = np.fromiter(labels, dtype='int32')
            write_score('results/{}/{}'.format(name, pipeline_name), labels, probs, classes_, (0, 2))

if __name__ == '__main__':
    main()