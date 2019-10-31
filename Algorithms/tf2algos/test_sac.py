import numpy as np
import tensorflow as tf
import tensorflow_probability as tfp
import Nn
from utils.sth import sth
from .policy import Policy


class SAC_NO_V(Policy):
    def __init__(self,
                 s_dim,
                 visual_sources,
                 visual_resolution,
                 a_dim_or_list,
                 action_type,
                 max_episode=50000,
                 gamma=0.99,
                 batch_size=128,
                 buffer_size=10000,
                 use_priority=False,
                 n_step=False,
                 base_dir=None,

                 alpha=0.2,
                 ployak=0.995,
                 discrete_tau=1.0,
                 auto_adaption=True,
                 lr=5.0e-4,
                 logger2file=False,
                 out_graph=False):
        super().__init__(
            s_dim=s_dim,
            visual_sources=visual_sources,
            visual_resolution=visual_resolution,
            a_dim_or_list=a_dim_or_list,
            action_type=action_type,
            gamma=gamma,
            max_episode=max_episode,
            base_dir=base_dir,
            policy_mode='OFF',
            batch_size=batch_size,
            buffer_size=buffer_size,
            use_priority=use_priority,
            n_step=n_step)
        self.lr = lr
        self.ployak = ployak
        self.discrete_tau = discrete_tau
        self.sigma_offset = np.full([self.a_counts, ], 0.01)
        self.log_alpha = alpha if not auto_adaption else tf.Variable(initial_value=0.0, name='log_alpha', dtype=tf.float32, trainable=True)
        self.auto_adaption = auto_adaption
        if self.action_type == 'continuous':
            self.actor_net = Nn.actor_continuous(self.s_dim, self.visual_dim, self.a_counts, 'actor_net')
        else:
            self.actor_net = Nn.actor_discrete(self.s_dim, self.visual_dim, self.a_counts, 'actor_net')
            self.gumbel_dist = tfp.distributions.Gumbel(0, 1)
        self.q1_net = Nn.critic_q_one(self.s_dim, self.visual_dim, self.a_counts, 'q1_net')
        self.q1_target_net = Nn.critic_q_one(self.s_dim, self.visual_dim, self.a_counts, 'q1_target_net')
        self.q2_net = Nn.critic_q_one(self.s_dim, self.visual_dim, self.a_counts, 'q2_net')
        self.q2_target_net = Nn.critic_q_one(self.s_dim, self.visual_dim, self.a_counts, 'q2_target_net')
        self.update_target_net_weights(
            self.q1_target_net.weights + self.q2_target_net.weights,
            self.q1_net.weights + self.q2_net.weights
        )
        self.optimizer_critic = tf.keras.optimizers.Adam(learning_rate=self.lr)
        self.optimizer_actor = tf.keras.optimizers.Adam(learning_rate=self.lr)
        self.optimizer_alpha = tf.keras.optimizers.Adam(learning_rate=self.lr)
        self.generate_recorder(
            logger2file=logger2file,
            model=self
        )
        self.recorder.logger.info('''
　　　　ｘｘｘｘｘｘｘ　　　　　　　　　　　ｘｘ　　　　　　　　　　　ｘｘｘｘｘｘ　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　ｘｘｘｘ　　ｘｘｘ　　　
　　　　ｘｘ　　　ｘｘ　　　　　　　　　　ｘｘｘ　　　　　　　　　　ｘｘｘ　　ｘｘ　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　ｘｘｘ　　　　ｘ　　　　
　　　　ｘｘ　　　　ｘ　　　　　　　　　　ｘｘｘ　　　　　　　　　　ｘｘ　　　　ｘｘ　　　　　　　ｘｘ　　　　　　　　　　　　　　　　ｘｘ　　　　　　　　　　ｘｘ　　　ｘｘ　　　　
　　　　ｘｘｘｘ　　　　　　　　　　　　　ｘ　ｘｘ　　　　　　　　　ｘｘ　　　　　　　　　　　　　ｘｘｘｘｘｘ　　　　　　　　　　ｘｘｘｘｘｘ　　　　　　　　ｘｘｘ　　ｘｘ　　　　
　　　　　ｘｘｘｘｘｘ　　　　　　　　　ｘｘ　ｘｘ　　　　　　　　ｘｘｘ　　　　　　　　　　　　　　ｘｘ　ｘｘ　　　　　　　　　　ｘｘ　　ｘｘ　　　　　　　　　ｘｘ　ｘｘ　　　　　
　　　　　　　　ｘｘｘ　　　　　　　　　ｘｘｘｘｘｘ　　　　　　　ｘｘｘ　　　　　　　　　　　　　　ｘ　　　ｘ　　　　　　　　　　ｘ　　　ｘｘ　　　　　　　　　ｘｘｘｘｘ　　　　　
　　　　ｘ　　　　ｘｘ　　　　　　　　ｘｘ　　　ｘｘ　　　　　　　　ｘｘ　　　　ｘｘ　　　　　　　　ｘ　　　ｘ　　　　　　　　　　ｘ　　　ｘｘ　　　　　　　　　　ｘｘｘ　　　　　　
　　　　ｘｘ　　　ｘｘ　　　　　　　　ｘｘ　　　ｘｘ　　　　　　　　ｘｘｘ　　ｘｘｘ　　　　　　　　ｘ　　　ｘ　　　　　　　　　　ｘｘ　　ｘｘ　　　　　　　　　　ｘｘｘ　　　　　　
　　　　ｘｘｘｘｘｘｘ　　　　　　　ｘｘｘ　　ｘｘｘｘｘ　　　　　　　ｘｘｘｘｘｘ　　　　　　　　ｘｘｘ　ｘｘｘ　　　　　　　　　ｘｘｘｘｘｘ　　　　　　　　　　　ｘ　　　　　　　
　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　ｘｘ　　　　　　　　　　　　　ｘ　　　
        ''')

    def choose_action(self, s, visual_s):
        a = self._get_action(s, visual_s)[-1].numpy()
        return a if self.action_type == 'continuous' else sth.int2action_index(a, self.a_dim_or_list)

    def choose_inference_action(self, s, visual_s):
        a = self._get_action(s, visual_s)[0].numpy()
        return a if self.action_type == 'continuous' else sth.int2action_index(a, self.a_dim_or_list)

    @tf.function
    def _get_action(self, vector_input, visual_input):
        with tf.device(self.device):
            if self.action_type == 'continuous':
                mu, sigma = self.actor_net(vector_input, visual_input)
                norm_dist = tfp.distributions.Normal(loc=mu, scale=sigma + self.sigma_offset)
                pi = tf.clip_by_value(norm_dist.sample(), -1, 1)
            else:
                logits = self.actor_net(vector_input, visual_input)
                mu = tf.argmax(logits, axis=1)
                cate_dist = tfp.distributions.Categorical(logits)
                pi = cate_dist.sample()
        return mu, pi

    def store_data(self, s, visual_s, a, r, s_, visual_s_, done):
        self.off_store(s, visual_s, a, r[:, np.newaxis], s_, visual_s_, done[:, np.newaxis])

    def learn(self, **kwargs):
        episode = kwargs['episode']
        for i in range(kwargs['step']):
            if self.data.is_lg_batch_size:
                s, visual_s, a, r, s_, visual_s_, done = self.data.sample()
                if self.use_priority:
                    self.IS_w = self.data.get_IS_w()
                actor_loss, critic_loss, entropy, td_error = self.train(s, visual_s, a, r, s_, visual_s_, done)
                if self.use_priority:
                    self.data.update(td_error, episode)
                self.update_target_net_weights(
                    self.q1_target_net.weights + self.q2_target_net.weights,
                    self.q1_net.weights + self.q2_net.weights,
                    self.ployak)
                tf.summary.experimental.set_step(self.global_step)
                tf.summary.scalar('LOSS/actor_loss', actor_loss)
                tf.summary.scalar('LOSS/critic_loss', critic_loss)
                tf.summary.scalar('LOSS/alpha', tf.exp(self.log_alpha))
                tf.summary.scalar('LOSS/entropy', entropy)
                tf.summary.scalar('LEARNING_RATE/lr', self.lr)
                self.recorder.writer.flush()

    @tf.function(experimental_relax_shapes=True)
    def train(self, s, visual_s, a, r, s_, visual_s_, done):
        with tf.device(self.device):
            with tf.GradientTape() as tape:
                if self.action_type == 'continuous':
                    mu, sigma = self.actor_net(s, visual_s)
                    ent = tf.reduce_mean(tfp.distributions.Normal(loc=mu, scale=sigma + self.sigma_offset).entropy())
                    target_mu, target_sigma = self.actor_net(s_, visual_s_)
                    target_norm_dist = tfp.distributions.Normal(loc=target_mu, scale=target_sigma + self.sigma_offset)
                    a_s_ = tf.clip_by_value(target_norm_dist.sample(), -1, 1)
                    a_s_log_prob_ = tf.reduce_mean(target_norm_dist.log_prob(a_s_), axis=1, keepdims=True)
                else:
                    target_logits = self.actor_net(s_, visual_s_)
                    target_cate_dist = tfp.distributions.Categorical(target_logits)
                    target_pi = target_cate_dist.sample()
                    a_s_log_prob_ = target_cate_dist.log_prob(target_pi)
                    a_s_ = tf.one_hot(target_pi, self.a_counts, dtype=tf.float32)
                q1 = self.q1_net(s, visual_s, a)
                q1_target = self.q1_target_net(s_, visual_s_, a_s_)
                q2 = self.q2_net(s, visual_s, a)
                q2_target = self.q2_target_net(s_, visual_s_, a_s_)
                dc_r_q1 = tf.stop_gradient(r + (1 - tf.exp(self.log_alpha)) * 0.2 * ent + self.gamma * (1 - done) * (q1_target - tf.exp(self.log_alpha) * a_s_log_prob_))
                dc_r_q2 = tf.stop_gradient(r + (1 - tf.exp(self.log_alpha)) * 0.2 * ent + self.gamma * (1 - done) * (q2_target - tf.exp(self.log_alpha) * a_s_log_prob_))
                td_error1 = q1 - dc_r_q1
                td_error2 = q2 - dc_r_q2
                q1_loss = tf.reduce_mean(tf.square(td_error1) * self.IS_w)
                q2_loss = tf.reduce_mean(tf.square(td_error2) * self.IS_w)
                critic_loss = 0.5 * q1_loss + 0.5 * q2_loss
            critic_grads = tape.gradient(critic_loss, self.q1_net.trainable_variables + self.q2_net.trainable_variables)
            self.optimizer_critic.apply_gradients(
                zip(critic_grads, self.q1_net.trainable_variables + self.q2_net.trainable_variables)
            )

            with tf.GradientTape() as tape:
                if self.action_type == 'continuous':
                    mu, sigma = self.actor_net(s, visual_s)
                    norm_dist = tfp.distributions.Normal(loc=mu, scale=sigma + self.sigma_offset)
                    pi = tf.clip_by_value(norm_dist.sample(), -1, 1)
                    a_s_log_prob = tf.reduce_mean(norm_dist.log_prob(pi), axis=1, keepdims=True)
                    entropy = tf.reduce_mean(norm_dist.entropy())
                else:
                    logits = self.actor_net(s, visual_s)
                    logp_all = tf.nn.log_softmax(logits)
                    gumbel_noise = tf.cast(self.gumbel_dist.sample([a.shape[0], self.a_counts]), dtype=tf.float32)
                    _pi = tf.nn.softmax((logp_all + gumbel_noise) / self.discrete_tau)
                    _pi_true_one_hot = tf.one_hot(tf.argmax(_pi, axis=-1), self.a_counts)
                    _pi_diff = tf.stop_gradient(_pi_true_one_hot - _pi)
                    pi = _pi_diff + _pi
                    a_s_log_prob = tf.reduce_sum(tf.multiply(logp_all, pi), axis=1, keepdims=True)
                    entropy = -tf.reduce_mean(tf.reduce_sum(tf.exp(logp_all) * logp_all, axis=1, keepdims=True))
                q1_s_pi = self.q1_net(s, visual_s, pi)
                q2_s_pi = self.q2_net(s, visual_s, pi)
                actor_loss = -tf.reduce_mean(tf.minimum(q1_s_pi, q2_s_pi) - tf.exp(self.log_alpha) * a_s_log_prob)
            actor_grads = tape.gradient(actor_loss, self.actor_net.trainable_variables)
            self.optimizer_actor.apply_gradients(
                zip(actor_grads, self.actor_net.trainable_variables)
            )

            if self.auto_adaption:
                with tf.GradientTape() as tape:
                    if self.action_type == 'continuous':
                        mu, sigma = self.actor_net(s, visual_s)
                        log_prob = tf.reduce_mean(tfp.distributions.Normal(loc=mu, scale=sigma + self.sigma_offset).log_prob(a), axis=1, keepdims=True)
                        target_mu, target_sigma = self.actor_net(s_, visual_s_)
                        target_norm_dist = tfp.distributions.Normal(loc=target_mu, scale=target_sigma + self.sigma_offset)
                        pi = tf.clip_by_value(target_norm_dist.sample(), -1, 1)
                        a_s_log_prob = tf.reduce_mean(target_norm_dist.log_prob(pi), axis=1, keepdims=True)
                    else:
                        logits = self.actor_net(s, visual_s)
                        cate_dist = tfp.distributions.Categorical(logits)
                        pi = cate_dist.sample()
                        a_s_log_prob = cate_dist.log_prob(pi)
                    alpha_loss = -tf.reduce_mean(self.log_alpha * tf.stop_gradient(a_s_log_prob + 0.2 * log_prob - self.a_counts))
                alpha_grads = tape.gradient(alpha_loss, [self.log_alpha])
                self.optimizer_alpha.apply_gradients(
                    zip(alpha_grads, [self.log_alpha])
                )
            self.global_step.assign_add(1)
            return actor_loss, critic_loss, entropy, td_error1 + td_error2 / 2