# -*- coding: utf-8 -*-
from __future__ import print_function as _
from __future__ import division as _
from __future__ import absolute_import as _
import os
import traceback

import numpy as np

from .graphdef_to_ssa import graphdef_to_ssa
from .graph_pass import *
from ..common_pass import common_pass


def load(tfgraph, resume_on_errors=False, **kwargs):
    """
    Loads a NetworkEnsemble from a Tensorflow frozen graph.
    tfgraph should either be a TensorFlow Graph object, or a path to a 
    frozen graph.

    Parameters
    ----------
    tfgraph : tf.Graph or str
        Either a path to a frozen graph, or a TensorFlow Graph object

    resume_on_errors : bool, optional. Default False
        This flag should generally be False except for debugging purposes
        for diagnosing 'unconvertible' graphs. Setting this flag to True
        will cause graph pass errors to be ignored, forcefully returning
        a NetworkEnsemble object.
    """
    if hasattr(tfgraph, 'as_graph_def'):
        gd = tfgraph.as_graph_def(add_shapes=True)
    else:
        gd = tfgraph

    ssa = graphdef_to_ssa(gd)

    placeholder_shape = kwargs.get("placeholder_shape", {})
    for k, v in placeholder_shape.items():
        assert (k in ssa.functions['main'].graph)
        ssa.functions['main'].graph[k].tfattr['_output_shapes'] = [v]

    passes = [
        delete_asserts, functionalize_loops, constant_propagation, cond_to_where,
        remove_variable_nodes, fusedbatchnorm_rewrite, lstmblockcell_rewrite
    ]

    if resume_on_errors == False:
        for p in passes:
            p(ssa)
    else:
        for p in passes:
            try:
                p(ssa)
            except:
                tb = traceback.format_exc()
                print("Exception in pass " + str(p))
                print(tb)
                print("Ignoring and continuing to next pass")

    common_pass(ssa)

    for f in ssa.functions.values():
        f.find_inputs_and_outputs()
    # check that type inference is complete
    if resume_on_errors == False:
        for f in ssa.functions.values():
            for n in f.graph.values():
                assert (n.datatype is not None)
    return ssa
