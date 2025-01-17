import json
import logging
import os
from collections import deque, Counter
from random import choice
import numpy as np
from tqdm import tqdm
from src.models.deepspeaker.audio_ds import pad_mfcc, Audio
from src.models.deepspeaker.conv_models import DeepSpeakerModel
from src.models.deepspeaker.utils import train_test_sp_to_utt

logger = logging.getLogger(__name__)


def extract_speaker(utt_file):
    return utt_file.split('/')[-1].split('_')[0]


def sample_from_mfcc(mfcc, max_length):
    if mfcc.shape[0] >= max_length:
        r = choice(range(0, len(mfcc) - max_length + 1))
        s = mfcc[r:r + max_length]
    else:
        s = pad_mfcc(mfcc, max_length)
    return np.expand_dims(s, axis=-1)


def sample_from_mfcc_file(utterance_file, max_length):
    mfcc = np.load(utterance_file)
    return sample_from_mfcc(mfcc, max_length)


class SparseCategoricalSpeakers:

    def __init__(self, speakers_list):
        self.speaker_ids = sorted(speakers_list)
        # all unique.
        assert len(set(self.speaker_ids)) == len(self.speaker_ids)
        self.map = dict(zip(self.speaker_ids, range(len(self.speaker_ids))))

    def get_index(self, speaker_id):
        return self.map[speaker_id]


class OneHotSpeakers:

    def __init__(self, speakers_list):
        from tensorflow.keras.utils import to_categorical
        self.speaker_ids = sorted(speakers_list)
        self.int_speaker_ids = list(range(len(self.speaker_ids)))
        self.map_speakers_to_index = dict(
            [(k, v) for (k, v) in zip(self.speaker_ids, self.int_speaker_ids)])
        self.map_index_to_speakers = dict(
            [(v, k) for (k, v) in zip(self.speaker_ids, self.int_speaker_ids)])
        self.speaker_categories = to_categorical(
            self.int_speaker_ids, num_classes=len(self.speaker_ids))

    def get_speaker_from_index(self, index):
        return self.map_index_to_speakers[index]

    def get_one_hot(self, speaker_id):
        index = self.map_speakers_to_index[speaker_id]
        return self.speaker_categories[index]


class LazyTripletBatcher:
    def __init__(self, working_dir: str, max_length: int, model: DeepSpeakerModel):
        self.working_dir = working_dir
        self.audio = Audio(cache_dir=working_dir)
        logger.info(f'Picking audio from {working_dir}.')
        self.sp_to_utt_train = train_test_sp_to_utt(self.audio, is_test=False)
        self.sp_to_utt_test = train_test_sp_to_utt(self.audio, is_test=True)
        self.max_length = max_length
        self.model = model
        self.nb_per_speaker = 2
        self.nb_speakers = 640
        self.history_length = 4
        self.history_every = 100  # batches.
        self.total_history_length = self.nb_speakers * \
            self.nb_per_speaker * self.history_length  # 25,600
        self.metadata_train_speakers = Counter()
        self.metadata_output_file = os.path.join(
            self.working_dir, 'debug_batcher.json')

        self.history_embeddings_train = deque(maxlen=self.total_history_length)
        self.history_utterances_train = deque(maxlen=self.total_history_length)
        self.history_model_inputs_train = deque(
            maxlen=self.total_history_length)

        self.history_embeddings = None
        self.history_utterances = None
        self.history_model_inputs = None

        self.batch_count = 0
        # init history.
        for _ in tqdm(range(self.history_length), desc='Initializing the batcher'):
            self.update_triplets_history()

    def update_triplets_history(self):
        model_inputs = []
        speakers = list(self.audio.speakers_to_utterances.keys())
        np.random.shuffle(speakers)
        selected_speakers = speakers[: self.nb_speakers]
        embeddings_utterances = []
        for speaker_id in selected_speakers:
            train_utterances = self.sp_to_utt_train[speaker_id]
            for selected_utterance in np.random.choice(a=train_utterances, size=self.nb_per_speaker, replace=False):
                mfcc = sample_from_mfcc_file(
                    selected_utterance, self.max_length)
                embeddings_utterances.append(selected_utterance)
                model_inputs.append(mfcc)
        embeddings = self.model.m.predict(np.array(model_inputs))
        assert embeddings.shape[-1] == 512
        embeddings = np.reshape(
            embeddings, (len(selected_speakers), self.nb_per_speaker, 512))
        self.history_embeddings_train.extend(
            list(embeddings.reshape((-1, 512))))
        self.history_utterances_train.extend(embeddings_utterances)
        self.history_model_inputs_train.extend(model_inputs)

        # reason: can't index a deque with a np.array.
        self.history_embeddings = np.array(self.history_embeddings_train)
        self.history_utterances = np.array(self.history_utterances_train)
        self.history_model_inputs = np.array(self.history_model_inputs_train)

        with open(self.metadata_output_file, 'w') as w:
            json.dump(obj=dict(self.metadata_train_speakers), fp=w, indent=2)

    def get_batch(self, batch_size, is_test=False):
        return self.get_batch_test(batch_size) if is_test else self.get_random_batch(batch_size, is_test=False)

    def get_batch_test(self, batch_size):
        return self.get_random_batch(batch_size, is_test=True)

    def get_random_batch(self, batch_size, is_test=False):
        sp_to_utt = self.sp_to_utt_test if is_test else self.sp_to_utt_train
        speakers = list(self.audio.speakers_to_utterances.keys())
        anchor_speakers = np.random.choice(
            speakers, size=batch_size // 3, replace=False)

        anchor_utterances = []
        positive_utterances = []
        negative_utterances = []
        for anchor_speaker in anchor_speakers:
            negative_speaker = np.random.choice(
                list(set(speakers) - {anchor_speaker}), size=1)[0]
            assert negative_speaker != anchor_speaker
            pos_utterances = np.random.choice(
                sp_to_utt[anchor_speaker], 2, replace=False)
            neg_utterance = np.random.choice(
                sp_to_utt[negative_speaker], 1, replace=True)[0]
            anchor_utterances.append(pos_utterances[0])
            positive_utterances.append(pos_utterances[1])
            negative_utterances.append(neg_utterance)

        # anchor and positive should have difference utterances (but same speaker!).
        anc_pos = np.array([positive_utterances, anchor_utterances])
        assert np.all(anc_pos[0, :] != anc_pos[1, :])
        assert np.all(np.array([extract_speaker(s) for s in anc_pos[0, :]]) == np.array(
            [extract_speaker(s) for s in anc_pos[1, :]]))

        pos_neg = np.array([positive_utterances, negative_utterances])
        assert np.all(pos_neg[0, :] != pos_neg[1, :])
        assert np.all(np.array([extract_speaker(s) for s in pos_neg[0, :]]) != np.array(
            [extract_speaker(s) for s in pos_neg[1, :]]))

        batch_x = np.vstack([
            [sample_from_mfcc_file(u, self.max_length)
             for u in anchor_utterances],
            [sample_from_mfcc_file(u, self.max_length)
             for u in positive_utterances],
            [sample_from_mfcc_file(u, self.max_length)
             for u in negative_utterances]
        ])

        # dummy. sparse softmax needs something.
        batch_y = np.zeros(shape=(len(batch_x), 1))
        return batch_x, batch_y

    def get_batch_train(self, batch_size):
        from test import batch_cosine_similarity
        # s1 = time()
        self.batch_count += 1
        if self.batch_count % self.history_every == 0:
            self.update_triplets_history()

        all_indexes = range(len(self.history_embeddings_train))
        anchor_indexes = np.random.choice(
            a=all_indexes, size=batch_size // 3, replace=False)

        # s2 = time()
        similar_negative_indexes = []
        dissimilar_positive_indexes = []
        # could be made parallel.
        for anchor_index in anchor_indexes:
            # s21 = time()
            anchor_embedding = self.history_embeddings[anchor_index]
            anchor_speaker = extract_speaker(
                self.history_utterances[anchor_index])

            # why self.nb_speakers // 2? just random. because it is fast. otherwise it's too much.
            negative_indexes = [j for (j, a) in enumerate(self.history_utterances)
                                if extract_speaker(a) != anchor_speaker]
            negative_indexes = np.random.choice(
                negative_indexes, size=self.nb_speakers // 2)

            # s22 = time()

            anchor_embedding_tile = [anchor_embedding] * len(negative_indexes)
            anchor_cos = batch_cosine_similarity(
                anchor_embedding_tile, self.history_embeddings[negative_indexes])

            # s23 = time()
            similar_negative_index = negative_indexes[np.argsort(
                anchor_cos)[-1]]  # [-1:]
            similar_negative_indexes.append(similar_negative_index)

            # s24 = time()
            positive_indexes = [j for (j, a) in enumerate(self.history_utterances) if
                                extract_speaker(a) == anchor_speaker and j != anchor_index]
            # s25 = time()
            anchor_embedding_tile = [anchor_embedding] * len(positive_indexes)
            # s26 = time()
            anchor_cos = batch_cosine_similarity(
                anchor_embedding_tile, self.history_embeddings[positive_indexes])
            dissimilar_positive_index = positive_indexes[np.argsort(anchor_cos)[
                0]]  # [:1]
            dissimilar_positive_indexes.append(dissimilar_positive_index)
            # s27 = time()

        # s3 = time()
        batch_x = np.vstack([
            self.history_model_inputs[anchor_indexes],
            self.history_model_inputs[dissimilar_positive_indexes],
            self.history_model_inputs[similar_negative_indexes]
        ])

        # s4 = time()

        # for anchor, positive, negative in zip(history_utterances[anchor_indexes],
        #                                       history_utterances[dissimilar_positive_indexes],
        #                                       history_utterances[similar_negative_indexes]):
        # print('anchor', os.path.basename(anchor),
        #       'positive', os.path.basename(positive),
        #       'negative', os.path.basename(negative))
        # print('_' * 80)

        # assert utterances as well positive != anchor.
        anchor_speakers = [extract_speaker(
            a) for a in self.history_utterances[anchor_indexes]]
        positive_speakers = [extract_speaker(
            a) for a in self.history_utterances[dissimilar_positive_indexes]]
        negative_speakers = [extract_speaker(
            a) for a in self.history_utterances[similar_negative_indexes]]

        assert len(anchor_indexes) == len(dissimilar_positive_indexes)
        assert len(similar_negative_indexes) == len(
            dissimilar_positive_indexes)
        assert list(self.history_utterances[dissimilar_positive_indexes]) != list(
            self.history_utterances[anchor_indexes])
        assert anchor_speakers == positive_speakers
        assert negative_speakers != anchor_speakers

        # dummy. sparse softmax needs something.
        batch_y = np.zeros(shape=(len(batch_x), 1))

        for a in anchor_speakers:
            self.metadata_train_speakers[a] += 1
        for a in positive_speakers:
            self.metadata_train_speakers[a] += 1
        for a in negative_speakers:
            self.metadata_train_speakers[a] += 1

        # s5 = time()
        # print('1-2', s2 - s1)
        # print('2-3', s3 - s2)
        # print('3-4', s4 - s3)
        # print('4-5', s5 - s4)
        # print('21-22', (s22 - s21) * (batch_size // 3))
        # print('22-23', (s23 - s22) * (batch_size // 3))
        # print('23-24', (s24 - s23) * (batch_size // 3))
        # print('24-25', (s25 - s24) * (batch_size // 3))
        # print('25-26', (s26 - s25) * (batch_size // 3))
        # print('26-27', (s27 - s26) * (batch_size // 3))

        return batch_x, batch_y

    def get_speaker_verification_data(self, anchor_speaker, num_different_speakers):
        speakers = list(self.audio.speakers_to_utterances.keys())
        anchor_utterances = []
        positive_utterances = []
        negative_utterances = []
        negative_speakers = np.random.choice(
            list(set(speakers) - {anchor_speaker}), size=num_different_speakers)
        assert [negative_speaker !=
                anchor_speaker for negative_speaker in negative_speakers]
        pos_utterances = np.random.choice(
            self.sp_to_utt_test[anchor_speaker], 2, replace=False)
        neg_utterances = [np.random.choice(self.sp_to_utt_test[neg], 1, replace=True)[
            0] for neg in negative_speakers]
        anchor_utterances.append(pos_utterances[0])
        positive_utterances.append(pos_utterances[1])
        negative_utterances.extend(neg_utterances)

        # anchor and positive should have difference utterances (but same speaker!).
        anc_pos = np.array([positive_utterances, anchor_utterances])
        assert np.all(anc_pos[0, :] != anc_pos[1, :])
        assert np.all(np.array([extract_speaker(s) for s in anc_pos[0, :]]) == np.array(
            [extract_speaker(s) for s in anc_pos[1, :]]))

        batch_x = np.vstack([
            [sample_from_mfcc_file(u, self.max_length)
             for u in anchor_utterances],
            [sample_from_mfcc_file(u, self.max_length)
             for u in positive_utterances],
            [sample_from_mfcc_file(u, self.max_length)
             for u in negative_utterances]
        ])

        # dummy. sparse softmax needs something.
        batch_y = np.zeros(shape=(len(batch_x), 1))
        return batch_x, batch_y


class TripletBatcher:

    def __init__(self, kx_train, ky_train, kx_test, ky_test):
        self.kx_train = kx_train
        self.ky_train = ky_train
        self.kx_test = kx_test
        self.ky_test = ky_test
        speakers_list = sorted(set(ky_train.argmax(axis=1)))
        num_different_speakers = len(speakers_list)
        # train speakers = test speakers.
        assert speakers_list == sorted(set(ky_test.argmax(axis=1)))
        assert speakers_list == list(range(num_different_speakers))
        self.train_indices_per_speaker = {}
        self.test_indices_per_speaker = {}

        for speaker_id in speakers_list:
            self.train_indices_per_speaker[speaker_id] = list(
                np.where(ky_train.argmax(axis=1) == speaker_id)[0])
            self.test_indices_per_speaker[speaker_id] = list(
                np.where(ky_test.argmax(axis=1) == speaker_id)[0])

        # check.
        # print(sorted(sum([v for v in self.train_indices_per_speaker.values()], [])))
        # print(range(len(ky_train)))
        assert sorted(sum([v for v in self.train_indices_per_speaker.values()], [
        ])) == sorted(range(len(ky_train)))
        assert sorted(sum([v for v in self.test_indices_per_speaker.values()], [
        ])) == sorted(range(len(ky_test)))
        self.speakers_list = speakers_list

    def select_speaker_data(self, speaker, n, is_test):
        x = self.kx_test if is_test else self.kx_train
        indices_per_speaker = self.test_indices_per_speaker if is_test else self.train_indices_per_speaker
        indices = np.random.choice(indices_per_speaker[speaker], size=n)
        return x[indices]

    def get_batch(self, batch_size, is_test=False):
        # y = self.ky_test if is_test else self.ky_train

        two_different_speakers = np.random.choice(
            self.speakers_list, size=2, replace=False)
        anchor_positive_speaker = two_different_speakers[0]
        negative_speaker = two_different_speakers[1]
        assert negative_speaker != anchor_positive_speaker

        batch_x = np.vstack([
            self.select_speaker_data(
                anchor_positive_speaker, batch_size // 3, is_test),
            self.select_speaker_data(
                anchor_positive_speaker, batch_size // 3, is_test),
            self.select_speaker_data(
                negative_speaker, batch_size // 3, is_test)
        ])

        batch_y = np.zeros(shape=(len(batch_x), len(self.speakers_list)))
        return batch_x, batch_y


class TripletBatcherMiner(TripletBatcher):

    def __init__(self, kx_train, ky_train, kx_test, ky_test, model: DeepSpeakerModel):
        super().__init__(kx_train, ky_train, kx_test, ky_test)
        self.model = model
        self.num_evaluations_to_find_best_batch = 10

    def get_batch(self, batch_size, is_test=False):
        if is_test:
            return super().get_batch(batch_size, is_test)
        max_loss = 0
        max_batch = None, None
        for i in range(self.num_evaluations_to_find_best_batch):
            # only train here.
            bx, by = super().get_batch(batch_size, is_test=False)
            loss = self.model.m.evaluate(
                bx, by, batch_size=batch_size, verbose=0)
            if loss > max_loss:
                max_loss = loss
                max_batch = bx, by
        return max_batch


class TripletBatcherSelectHardNegatives(TripletBatcher):

    def __init__(self, kx_train, ky_train, kx_test, ky_test, model: DeepSpeakerModel):
        super().__init__(kx_train, ky_train, kx_test, ky_test)
        self.model = model

    def get_batch(self, batch_size, is_test=False, predict=None):
        if predict is None:
            predict = self.model.m.predict
        from test import batch_cosine_similarity
        num_triplets = batch_size // 3
        inputs = []
        k = 2  # do not change this.
        for speaker in self.speakers_list:
            inputs.append(self.select_speaker_data(
                speaker, n=k, is_test=is_test))
        # num_speakers * [k, num_frames, num_fbanks, 1].
        inputs = np.array(inputs)
        embeddings = predict(np.vstack(inputs))
        assert embeddings.shape[-1] == 512
        # (speaker, utterance, 512)
        embeddings = np.reshape(embeddings, (len(self.speakers_list), k, 512))
        cs = batch_cosine_similarity(embeddings[:, 0], embeddings[:, 1])
        arg_sort = np.argsort(cs)
        assert len(arg_sort) > num_triplets
        anchor_speakers = arg_sort[0:num_triplets]

        anchor_embeddings = embeddings[anchor_speakers, 0]
        negative_speakers = sorted(
            set(self.speakers_list) - set(anchor_speakers))
        negative_embeddings = embeddings[negative_speakers, 0]

        selected_negative_speakers = []
        for anchor_embedding in anchor_embeddings:
            cs_negative = [batch_cosine_similarity(
                [anchor_embedding], neg) for neg in negative_embeddings]
            selected_negative_speakers.append(
                negative_speakers[int(np.argmax(cs_negative))])

        # anchor with frame 0.
        # positive with frame 1.
        # negative with frame 0.
        assert len(set(selected_negative_speakers).intersection(
            anchor_speakers)) == 0
        negative = inputs[selected_negative_speakers, 0]
        positive = inputs[anchor_speakers, 1]
        anchor = inputs[anchor_speakers, 0]
        batch_x = np.vstack([anchor, positive, negative])
        batch_y = np.zeros(shape=(len(batch_x), len(self.speakers_list)))
        return batch_x, batch_y


class TripletEvaluator:

    def __init__(self, kx_test, ky_test):
        self.kx_test = kx_test
        self.ky_test = ky_test
        speakers_list = sorted(set(ky_test.argmax(axis=1)))
        num_different_speakers = len(speakers_list)
        assert speakers_list == list(range(num_different_speakers))
        self.test_indices_per_speaker = {}
        for speaker_id in speakers_list:
            self.test_indices_per_speaker[speaker_id] = list(
                np.where(ky_test.argmax(axis=1) == speaker_id)[0])
        assert sorted(sum([v for v in self.test_indices_per_speaker.values()], [
        ])) == sorted(range(len(ky_test)))
        self.speakers_list = speakers_list

    def _select_speaker_data(self, speaker):
        indices = np.random.choice(
            self.test_indices_per_speaker[speaker], size=1)
        return self.kx_test[indices]

    def get_speaker_verification_data(self, positive_speaker, num_different_speakers):
        all_negative_speakers = list(
            set(self.speakers_list) - {positive_speaker})
        assert len(self.speakers_list) - 1 == len(all_negative_speakers)
        negative_speakers = np.random.choice(
            all_negative_speakers, size=num_different_speakers, replace=False)
        assert positive_speaker not in negative_speakers
        anchor = self._select_speaker_data(positive_speaker)
        positive = self._select_speaker_data(positive_speaker)
        data = [anchor, positive]
        data.extend([self._select_speaker_data(n) for n in negative_speakers])
        return np.vstack(data)
