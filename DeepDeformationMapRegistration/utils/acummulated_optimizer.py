from tensorflow.python.keras.optimizers import Optimizer
from tensorflow.python.keras.optimizer_v2.optimizer_v2 import OptimizerV2
from tensorflow.python import ops, math_ops, state_ops, control_flow_ops
from tensorflow.python.keras import backend as K
from tensorflow.python.keras import backend_config
import tensorflow as tf


class AccumOptimizer(Optimizer):
    """Optimizer
    Inheriting Optimizer class, wrapping the original optimizer
    to achieve a new corresponding optimizer of gradient accumulation.
    # Arguments
        optimizer: an instance of keras optimizer (supporting
                    all keras optimizers currently available);
        steps_per_update: the steps of gradient accumulation
    # Returns
        a new keras optimizer.
    """
    def __init__(self, optimizer, steps_per_update=1, **kwargs):
        super(AccumOptimizer, self).__init__(name='AccumOptimizer', **kwargs)
        self.optimizer = optimizer
        with K.name_scope(self.__class__.__name__):
            self.steps_per_update = steps_per_update
            self.iterations = K.variable(0, dtype='int64', name='iterations')
            self.cond = K.equal(self.iterations % self.steps_per_update, 0)
            self.lr = self.optimizer.lr
            self.optimizer.lr = K.switch(self.cond, self.optimizer.lr, 0.)
            for attr in ['momentum', 'rho', 'beta_1', 'beta_2']:
                if hasattr(self.optimizer, attr):
                    value = getattr(self.optimizer, attr)
                    setattr(self, attr, value)
                    setattr(self.optimizer, attr, K.switch(self.cond, value, 1 - 1e-7))
            for attr in self.optimizer.get_config():
                if not hasattr(self, attr):
                    value = getattr(self.optimizer, attr)
                    setattr(self, attr, value)
            # Cover the original get_gradients method with accumulative gradients.
            def get_gradients(loss, params):
                return [ag / self.steps_per_update for ag in self.accum_grads]
            self.optimizer.get_gradients = get_gradients
    def get_updates(self, loss, params):
        self.updates = [
            K.update_add(self.iterations, 1),
            K.update_add(self.optimizer.iterations, K.cast(self.cond, 'int64')),
        ]
        # gradient accumulation
        self.accum_grads = [K.zeros(K.int_shape(p), dtype=K.dtype(p)) for p in params]
        grads = self.get_gradients(loss, params)
        for g, ag in zip(grads, self.accum_grads):
            self.updates.append(K.update(ag, K.switch(self.cond, g, ag + g)))
        # inheriting updates of original optimizer
        self.updates.extend(self.optimizer.get_updates(loss, params)[1:])
        self.weights.extend(self.optimizer.weights)
        return self.updates
    def get_config(self):
        iterations = K.eval(self.iterations)
        K.set_value(self.iterations, 0)
        config = self.optimizer.get_config()
        K.set_value(self.iterations, iterations)
        return config


__all__ = ['AdamAccumulated']


# SRC: https://github.com/CyberZHG/keras-gradient-accumulation/blob/master/keras_gradient_accumulation/optimizer_v2.py
class AdamAccumulated(OptimizerV2):
    """Optimizer that implements the Adam algorithm with gradient accumulation."""

    def __init__(self,
                 accumulation_steps,
                 learning_rate=0.001,
                 beta_1=0.9,
                 beta_2=0.999,
                 epsilon=1e-7,
                 amsgrad=False,
                 name='Adam',
                 **kwargs):
        r"""Construct a new Adam optimizer.
        Args:
            accumulation_steps: An integer. Update gradient in every accumulation steps.
            learning_rate: A Tensor or a floating point value.    The learning rate.
            beta_1: A float value or a constant float tensor. The exponential decay
                rate for the 1st moment estimates.
            beta_2: A float value or a constant float tensor. The exponential decay
                rate for the 2nd moment estimates.
            epsilon: A small constant for numerical stability. This epsilon is
                "epsilon hat" in the Kingma and Ba paper (in the formula just before
                Section 2.1), not the epsilon in Algorithm 1 of the paper.
            amsgrad: boolean. Whether to apply AMSGrad variant of this algorithm from
                the paper "On the Convergence of Adam and beyond".
            name: Optional name for the operations created when applying gradients.
                Defaults to "Adam".    @compatibility(eager) When eager execution is
                enabled, `learning_rate`, `beta_1`, `beta_2`, and `epsilon` can each be
                a callable that takes no arguments and returns the actual value to use.
                This can be useful for changing these values across different
                invocations of optimizer functions. @end_compatibility
            **kwargs: keyword arguments. Allowed to be {`clipnorm`, `clipvalue`, `lr`,
                `decay`}. `clipnorm` is clip gradients by norm; `clipvalue` is clip
                gradients by value, `decay` is included for backward compatibility to
                allow time inverse decay of learning rate. `lr` is included for backward
                compatibility, recommended to use `learning_rate` instead.
        """

        super(AdamAccumulated, self).__init__(name, **kwargs)
        self._set_hyper('accumulation_steps', accumulation_steps)
        self._set_hyper('learning_rate', kwargs.get('lr', learning_rate))
        self._set_hyper('decay', self._initial_decay)
        self._set_hyper('beta_1', beta_1)
        self._set_hyper('beta_2', beta_2)
        self.epsilon = epsilon or backend_config.epsilon()
        self.amsgrad = amsgrad

    def _create_slots(self, var_list):
        for var in var_list:
            self.add_slot(var, 'g')
        for var in var_list:
            self.add_slot(var, 'm')
        for var in var_list:
            self.add_slot(var, 'v')
        if self.amsgrad:
            for var in var_list:
                self.add_slot(var, 'vhat')

    def set_weights(self, weights):
        params = self.weights
        num_vars = int((len(params) - 1) / 2)
        if len(weights) == 3 * num_vars + 1:
            weights = weights[:len(params)]
        super(AdamAccumulated, self).set_weights(weights)

    def _resource_apply_dense(self, grad, var):
        var_dtype = var.dtype.base_dtype
        lr_t = self._decayed_lr(var_dtype)
        beta_1_t = self._get_hyper('beta_1', var_dtype)
        beta_2_t = self._get_hyper('beta_2', var_dtype)
        accumulation_steps = self._get_hyper('accumulation_steps', 'int64')
        update_cond = tf.equal((self.iterations + 1) % accumulation_steps, 0)
        sub_step = self.iterations % accumulation_steps + 1
        local_step = math_ops.cast(self.iterations // accumulation_steps + 1, var_dtype)
        beta_1_power = math_ops.pow(beta_1_t, local_step)
        beta_2_power = math_ops.pow(beta_2_t, local_step)
        epsilon_t = ops.convert_to_tensor(self.epsilon, var_dtype)
        lr = (lr_t * math_ops.sqrt(1 - beta_2_power) / (1 - beta_1_power))
        lr = tf.compat.v1.where(update_cond, lr, 0.0)

        g = self.get_slot(var, 'g')
        g_a = grad / math_ops.cast(accumulation_steps, var_dtype)
        g_t = tf.compat.v1.where(tf.equal(sub_step, 1),
                       g_a,
                       g + (g_a - g) / math_ops.cast(sub_step, var_dtype))
        g_t = state_ops.assign(g, g_t, use_locking=self._use_locking)

        m = self.get_slot(var, 'm')
        m_t = tf.compat.v1.where(update_cond, m * beta_1_t + g_t * (1 - beta_1_t), m)
        m_t = state_ops.assign(m, m_t, use_locking=self._use_locking)

        v = self.get_slot(var, 'v')
        v_t = tf.compat.v1.where(update_cond, v * beta_2_t + (g_t * g_t) * (1 - beta_2_t), v)
        v_t = state_ops.assign(v, v_t, use_locking=self._use_locking)

        if not self.amsgrad:
            v_sqrt = math_ops.sqrt(v_t)
            var_update = state_ops.assign_sub(
                    var, lr * m_t / (v_sqrt + epsilon_t), use_locking=self._use_locking)
            return control_flow_ops.group(*[var_update, m_t, v_t])
        else:
            v_hat = self.get_slot(var, 'vhat')
            v_hat_t = tf.compat.v1.where(update_cond, math_ops.maximum(v_hat, v_t), v_hat)
            with ops.control_dependencies([v_hat_t]):
                v_hat_t = state_ops.assign(
                        v_hat, v_hat_t, use_locking=self._use_locking)
            v_hat_sqrt = math_ops.sqrt(v_hat_t)
            var_update = state_ops.assign_sub(
                    var,
                    lr * m_t / (v_hat_sqrt + epsilon_t),
                    use_locking=self._use_locking)
            return control_flow_ops.group(*[var_update, m_t, v_t, v_hat_t])

    def get_config(self):
        config = super(AdamAccumulated, self).get_config()
        config.update({
            'accumulation_steps': self._serialize_hyperparameter('accumulation_steps'),
            'learning_rate': self._serialize_hyperparameter('learning_rate'),
            'decay': self._serialize_hyperparameter('decay'),
            'beta_1': self._serialize_hyperparameter('beta_1'),
            'beta_2': self._serialize_hyperparameter('beta_2'),
            'epsilon': self.epsilon,
            'amsgrad': self.amsgrad,
        })
        return config
