import json
import os
import numpy as np
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2' 
import tensorflow as tf
from flask import Flask, jsonify, request, Response
from flask_restful import reqparse, abort, Api, Resource

import model, sample, encoder


os.environ["KMP_BLOCKTIME"] = "1"
os.environ["KMP_SETTINGS"] = "1"
os.environ["KMP_AFFINITY"] = "granularity=fine,verbose,compact,1,0"

def interact_model(model_name='model', seed=99, nsamples=5, batch_size=5,
                    length=8, temperature=0, top_k=10, top_p=.85, models_dir=''):

    models_dir = os.path.expanduser(os.path.expandvars(models_dir))

    if batch_size is None:
        batch_size = 1
    assert nsamples % batch_size == 0

    enc = encoder.get_encoder(model_name, models_dir)
    hparams = model.default_hparams()
    with open(os.path.join(models_dir, model_name, 'hparams.json')) as f:
        hparams.override_from_dict(json.load(f))

    if length is None:
        length = hparams.n_ctx // 2
    elif length > hparams.n_ctx:
        raise ValueError("Can't get samples longer than window size: %s" % hparams.n_ctx)

    gpu_options = tf.GPUOptions(allow_growth=True)
    config = tf.ConfigProto(intra_op_parallelism_threads=0, inter_op_parallelism_threads=0,
                       allow_soft_placement=True, gpu_options=gpu_options)

    with tf.Session(graph=tf.Graph(), config=config) as sess:

        context = tf.placeholder(tf.int32, [batch_size, None])
        np.random.seed(seed)
        tf.set_random_seed(seed)

        # p = tf.random.uniform((1,), minval=.68, maxval=.98, dtype=tf.dtypes.float32, name='random_p_logits')
        output = sample.sample_sequence(
            hparams=hparams, length=length,
            context=context,
            batch_size=batch_size,
            temperature=temperature, top_k=top_k, top_p=top_p
        )

        saver = tf.train.Saver()
        ckpt = tf.train.latest_checkpoint(os.path.join(models_dir, model_name))
        saver.restore(sess, ckpt)

        class Autocomplete(Resource):
            def get(self): return ''

            def post(self):
                body = request.get_json(force=True)
                if body['text'] == "": return

                context_tokens = enc.encode(body['text'])
                generated = 0
                predictions = []

                for _ in range(nsamples // batch_size):

                    feed_dict = {context: [context_tokens for _ in range(batch_size)]}
                    out = sess.run(output, feed_dict=feed_dict)[:, len(context_tokens):]

                    for i in range(batch_size):
                        generated += 1
                        text = enc.decode(out[i])
                        predictions.append(str(text))

                return Response(json.dumps({'result':predictions}), status=200, mimetype='application/json')

        app = Flask(__name__)
        api = Api(app)
        api.add_resource(Autocomplete, '/autocomplete')

        if __name__ == '__main__':
            app.run('0.0.0.0', port=3030, debug=True)

interact_model()