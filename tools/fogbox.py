"""
fogbox

populates a volume with geometry


expressions for translation to center in a Cube controller

x: Cube1.cube.r - (abs(Cube1.cube.r - Cube1.cube.x))/2
y: Cube1.cube.t - (abs(Cube1.cube.t - Cube1.cube.y))/2
z: Cube1.cube.f - ((abs(Cube1.cube.f - Cube1.cube.n)/3)*1)

nonlinear scaling expressions
Card1.translate - (1 * pow(Card1.translate-Card4.translate, -NoOp1.scalar))


"""

import nuke
import logging
from random import randint, choice

logger = logging.getLogger(__name__)


def create_cube():
    logger.debug("creating cube")
    # cube = nuke.createNode('Cube')

    cube = nuke.nodes.Cube()
    # configure as required
    cube.knob('display').setValue('wireframe')
    cube.knob('render_mode').setValue('off')
    cube.knob('cast_shadow').setValue(False)
    cube.knob('receive_shadow').setValue(False)
    cube.knob('rows').setValue(1)
    cube.knob('columns').setValue(1)

    # setup expressions to keep cube pivot in middle of cube volume
    cube.knob('pivot').setExpression('cube.x - ((cube.x - cube.r)/2)', 0)
    cube.knob('pivot').setExpression('cube.y - ((cube.y - cube.t)/2)', 1)
    cube.knob('pivot').setExpression('cube.f - ((cube.f - cube.n)/2)', 2)

    return cube


def create_card(cube, group, card_idx=1, ):
    logger.debug("creating card with index: {}".format(card_idx))
    card = nuke.nodes.Card()

    # get the cube 'name' as we'll need it a few times
    c_name = cube.name()

    # add custom knobs
    card_id_knob = nuke.Int_Knob('card_id', 'card ID')
    card_id_knob.setValue(card_idx)
    card.addKnob(card_id_knob)

    card_seed_knob = nuke.Int_Knob('seed', 'seed')
    card_seed_knob.setValue(generate_seed())
    card.addKnob(card_seed_knob)

    card_trans_z_formula = nuke.Double_Knob('card_trans_z')
    card_trans_z_formula.setExpression("(({0}.cube.f - (((abs({0}.cube.f - {0}.cube.n)/{1})*card_id)) / exp_scale) + (random(seed) * seed_sign) * xyz_var.z)".format(c_name, int(group.knob('num_cards').value()) + 1))
    card_trans_z_formula.setVisible(False)
    card.addKnob(card_trans_z_formula)

    seed_sign = nuke.Int_Knob('seed_sign')
    seed_sign.setValue(choice([-1, 1]))
    seed_sign.setVisible(False)

    card.addKnob(seed_sign)

    # setup the expressions for the transforms
    t_knob = card.knob('translate')
    if card_idx == 1:
        t_knob.setExpression("(({0}.cube.f - ((abs({0}.cube.f - {0}.cube.n)/{1})*card_id)) + (random(seed) * seed_sign) * xyz_var.z)".format(c_name, int(group.knob('num_cards').value()) + 1), 2)
    else:
        t_knob.setExpression("card_trans_z < Card1.translate ? card_trans_z : Card1.translate", 2)

    t_knob.setExpression("(({0}.cube.t - (abs({0}.cube.t - {0}.cube.y))/2)+((({0}.cube.t - {0}.cube.y)/2) * (random(seed) * seed_sign)) * xyz_var.y)".format(c_name), 1)
    t_knob.setExpression("(({0}.cube.r - (abs({0}.cube.r - {0}.cube.x))/2)+((({0}.cube.r - {0}.cube.x)/2) * (random(seed) * seed_sign)) * xyz_var.x)".format(c_name), 0)

    # set expressions to control the scale, so the card 'fill's the XY volume slice of the cube
    s_knob = card.knob('scaling')
    s_knob.setExpression("abs({0}.cube.x - {0}.cube.r)".format(c_name), 0)
    s_knob.setExpression("abs({0}.cube.y - {0}.cube.t)".format(c_name), 1)
    s_knob.setExpression("abs({0}.cube.f - {0}.cube.n)".format(c_name), 2)

    card.knob('uniform_scale').setExpression("card_scale + (scale_var * (random(seed) * seed_sign))")

    return card


def generate_seed():

    result = randint(1000, 9999)
    if result % 2 == 0:
        seed = -1 * result
    else:
        seed = result

    return seed


def update():

    # delete all cards and re-populate with the card count

    grp = nuke.thisNode()

    grp.begin()

    for node in grp.nodes():
        if node.Class() != "Cube":
            nuke.delete(node)

    _make_internals(grp.knob('num_cards').value(), grp)
    grp.knob('exp_scale').setRange(1, grp.knob('num_cards').value())

    grp.end()


def _make_internals(card_count, grp):

    input_node = nuke.nodes.Input()

    cards_scene = nuke.nodes.Scene()
    cube_scene = nuke.nodes.Scene()
    cards_tx_geo = nuke.nodes.TransformGeo()

    logger.debug('make_internals called')

    logger.debug('toNode(Cube1) is: {}'.format(nuke.toNode('Cube1')))
    # create cube
    if nuke.toNode('Cube1') is None:
        cube = create_cube()
    else:
        cube = nuke.toNode('Cube1')
    cube_scene.setInput(0, cube)

    # establish matrix link to cube
    cards_tx_geo.knob('useMatrix').setValue(True)
    cards_tx_geo.knob('matrix').setExpression('{}.matrix'.format(cube.name()))

    # create cards & inputs
    for i in range(1, card_count + 1):
        fh = nuke.nodes.FrameHold()
        rand_frame = nuke.Int_Knob('rand_frame')
        rand_frame.setVisible(False)

        fh.addKnob(rand_frame)
        fh.setInput(0, input_node)
        # fh.knob('first_frame').setExpression('seq_input ? ')
        fh.knob('disable').setExpression('![exists parent.input]')

        card = create_card(cube, grp, i)
        card.knob('image_aspect').setValue(False)
        card.setInput(0, fh)
        cards_scene.setInput(i, card)
        fh.knob('first_frame').setExpression('seq_input ? [topnode this.parent.input].first + {}-1 : [topnode this.parent.input].first + fmod(abs({}.seed) + [topnode this.parent.input].last-[topnode this.parent.input].first, [topnode this.parent.input].last-[topnode this.parent.input].first)'.format(i, card.name()))

    cards_tx_geo.setInput(0, cards_scene)
    cube_scene.setInput(1, cards_tx_geo)

    output_node = nuke.nodes.Output()
    output_node.setInput(0, cube_scene)


def run(card_count):

    # create group
    grp = nuke.createNode('Group')
    grp.setName('CE_FogBox')

    seq_input = nuke.Boolean_Knob('seq_input', 'sequential input?')
    seq_input.setValue(False)
    seq_input.setTooltip('set the input images to be assigned sequentially to each card from front to back')

    num_cards = nuke.Int_Knob('num_cards')
    num_cards.setValue(card_count)
    num_cards.setTooltip('modify the number of cards in the box')

    card_scale = nuke.Double_Knob('card_scale', 'scale')
    card_scale.setValue(1.0)
    card_scale.setTooltip('adjust the uniform scale for the cards in the box')

    card_var_scale = nuke.Double_Knob('scale_var', 'scale variation')
    card_var_scale.setValue(0.0)
    card_var_scale.setTooltip('scale each card\'s uniform scale, randomly, by a seed ')

    xyz_var = nuke.XYZ_Knob('xyz_var', 'variation')
    xyz_var.setValue(0, 0)
    xyz_var.setValue(0, 1)
    xyz_var.setValue(0, 2)
    xyz_var.setTooltip('Varies each card randomly (by a seed) in X/Y/Z axes')

    exp_scale = nuke.Double_Knob('exp_scale', 'exp scale')
    exp_scale.setValue(1.0)
    exp_scale.setRange(1.0, float(card_count))
    exp_scale.setTooltip('scale the cards towards the origin card in z, non-linearly')

    grp.addKnob(seq_input)
    grp.addKnob(num_cards)
    grp.addKnob(card_scale)
    grp.addKnob(card_var_scale)
    grp.addKnob(xyz_var)
    grp.addKnob(exp_scale)

    grp.knob('knobChanged').setValue("""
n = nuke.thisNode()
k = nuke.thisKnob()
if k.name() == 'num_cards':
    print "changing card numbers to {}".format(k.value())
    # ce_fogbox._make_internals(k.value(), n)
    ce_fogbox.update()
""")

    grp.begin()

    _make_internals(num_cards.value(), grp)

    grp.end()

    card_z_dist = nuke.Double_Knob('z_dist')
    card_z_dist.setVisible(False)
    card_z_dist.setExpression("Card1.translate.z - Card{}.translate.z".format(card_count))

    grp.addKnob(card_z_dist)

    return grp

