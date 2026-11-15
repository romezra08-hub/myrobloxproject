--!strict
-- PetAnimator: procedural idle and walk animation for the Mine an Egg pets.
--
-- Every pet is one rigid model (a body mesh plus glow or eye parts welded to it, no bones), so it is
-- animated as a whole: each frame the model is moved and turned a little around its pivot (under the
-- feet, in the middle), on top of where the pet-follow code wants it. Client only; the caller drives it.
--
--     local PetAnimator = require(ReplicatedStorage.PetAnimator)
--     local animator = PetAnimator.new(petModel, "Fox")        -- petName defaults to the model's name
--     -- every frame (RenderStepped / PreRender), after working out where the pet should stand:
--     animator:Step(dt, targetCFrame, speedInStudsPerSecond)
--     -- when the pet is removed:
--     animator:Destroy()
--
-- All the motion maths is in PetAnimator.offset, a pure function. models/anim/preview_anim.py is an
-- exact Python port of it (it reads the tables below straight from this file), used to render
-- previews in Blender. If you change a formula here, change it there too.
--
-- Conventions inside offset: lengths are fractions of the pet's height (so a dragon moves more studs
-- than a fox), angles are degrees, times are seconds. "pitch" is nose-down positive, "roll" positive
-- dips the pet's left side, "yaw" positive turns it to its left.

local PetAnimator = {}
PetAnimator.__index = PetAnimator

export type Profile = {
	hover: number, -- height above the ground, both idle and walking (x height)
	pivot: number, -- height of the point the pet turns around (x height); the feet are then kept on the floor
	-- idle
	breath: number, -- breathing / hover bob up and down (x height)
	breathPeriod: number, -- seconds per breath
	breathPitch: number, -- nod with each breath (degrees)
	look: number, -- look-around: turn left this far, then right a little less (degrees)
	lookTilt: number, -- head tilt that goes with the look (degrees)
	lookRaise: number, -- raise the front while looking (degrees)
	lookEvery: number, -- seconds from one look-around to the next
	lookTime: number, -- seconds a look-around lasts
	sway: number, -- weight shift: slow roll from side to side (degrees)
	swaySide: number, -- weight shift: slow slide from side to side (x height)
	swayPeriod: number, -- seconds per weight shift
	spin: number, -- slow turn back and forth (degrees)
	spinPeriod: number, -- seconds per turn back and forth
	figure: number, -- figure-eight drift, side to side (x height); up and down is half of it
	figurePeriod: number, -- seconds per figure eight
	figureBank: number, -- bank into the figure eight (degrees)
	idleHop: number, -- an occasional little hop in place (x height)
	idleHopEvery: number, -- seconds from one idle hop to the next
	idleHopTime: number, -- seconds an idle hop lasts
	idleHopTilt: number, -- nose up at take-off, down on landing (degrees)
	wobble: number, -- jelly wobble from side to side after landing a hop (degrees)
	wobbleTime: number, -- seconds the wobble after an idle hop lasts
	-- walk; one cycle is one stride, made of `beats` steps or hops
	walkHz: number, -- strides per second for a 3-stud pet at 16 studs/s (bigger pets stride slower)
	beats: number, -- steps or hops per stride: 2 for a trot, 1 for a hop or a flap
	duty: number, -- part of each beat spent in the air (1 = bouncing all the time, less = a pause between hops)
	bounce: number, -- height of each step or hop (x height)
	sharp: number, -- 0 = a smooth bob, 1 = a bouncy hop with a quick contact
	skip: number, -- every other hop is bigger by this much and the next smaller (a skip)
	lean: number, -- lean forward while moving (degrees)
	nod: number, -- nose up while rising, down while falling, each beat (degrees)
	roll: number, -- rock from side to side, one side per beat (degrees)
	yaw: number, -- swing left and right, one side per beat (degrees)
	side: number, -- slide left and right, one side per beat (x height)
	impact: number, -- nose dips just after each footfall, for heavy pets (degrees)
	bank: number, -- bank into turns (degrees per radian per second of turning)
	bankMax: number, -- largest bank (degrees)
}

export type State = {
	time: number, -- seconds, starting at a random phase
	cycle: number, -- walk cycles done, kept between 0 and 2
	blend: number, -- 0 idle .. 1 walking, smoothed (offset eases it)
	speed: number, -- studs per second, smoothed: what Step passes to offset
	turn: number, -- turning speed in radians per second, smoothed
	heading: number, -- last heading, to measure turning
	hasHeading: boolean,
	height: number, -- the model's size in studs, around its pivot
	width: number,
	length: number,
}

export type PetAnimator = typeof(setmetatable(
	{} :: {
		model: Model?,
		profile: Profile,
		state: State,
	},
	PetAnimator
))

-- Tuning shared by every pet.
local REF_SIZE = 3 -- studs: walkHz is for a pet this tall
local REF_SPEED = 16 -- studs per second: a player's walking speed
local WALK_START = 0.6 -- studs per second: below this the pet is idle
local WALK_FULL = 4 -- studs per second: above this the pet is fully walking
local BLEND_RATE = 5 -- how quickly idle and walk blend (per second)
local SPEED_RATE = 6 -- how quickly the speed the motion follows catches up (per second)
local TURN_RATE = 4 -- how quickly the measured turning speed follows (per second)
local TURN_MAX = 3 -- radians per second: faster turning is treated as this
local FOOT = 0.9 -- the feet cover this much of the model's width and length, for keeping them on the floor
local IMPACT_TIME = 0.15 -- part of a beat at which the heavy footfall nod is deepest
local TAU = 2 * math.pi

-- Every field, with the value used when a style does not set it.
local DEFAULTS: Profile = {
	hover = 0,
	pivot = 0.35,
	breath = 0,
	breathPeriod = 3,
	breathPitch = 0,
	look = 0,
	lookTilt = 0,
	lookRaise = 0,
	lookEvery = 7,
	lookTime = 3,
	sway = 0,
	swaySide = 0,
	swayPeriod = 5,
	spin = 0,
	spinPeriod = 8,
	figure = 0,
	figurePeriod = 5,
	figureBank = 0,
	idleHop = 0,
	idleHopEvery = 4,
	idleHopTime = 0.35,
	idleHopTilt = 0,
	wobble = 0,
	wobbleTime = 0.8,
	walkHz = 1.5,
	beats = 2,
	duty = 1,
	bounce = 0,
	sharp = 0,
	skip = 0,
	lean = 0,
	nod = 0,
	roll = 0,
	yaw = 0,
	side = 0,
	impact = 0,
	bank = 4,
	bankMax = 6,
}

-- The motion styles. Each sets only what differs from DEFAULTS.
PetAnimator.STYLES = {
	-- four-legged trot: a two-beat bounce, a small nod, a slight roll; idle breathing, a slow look round, weight shift
	walker = {
		pivot = 0.4,
		breath = 0.012,
		breathPeriod = 3.2,
		breathPitch = 0.7,
		look = 20,
		lookTilt = 3,
		lookEvery = 6.5,
		lookTime = 3.6,
		sway = 1.4,
		swaySide = 0.008,
		swayPeriod = 5.2,
		walkHz = 1.45,
		beats = 2,
		bounce = 0.028,
		sharp = 0.6,
		lean = 2,
		nod = 2.2,
		roll = 2.2,
		yaw = 1.5,
		side = 0.006,
		bank = 3,
	},
	-- small seated pets: breathing, a curious tilt and look round; a perky hop-skip when moving
	sitter = {
		pivot = 0.3,
		breath = 0.016,
		breathPeriod = 2.6,
		breathPitch = 1.2,
		look = 22,
		lookTilt = 9,
		lookEvery = 5.2,
		lookTime = 3.2,
		sway = 1.5,
		swayPeriod = 4.4,
		walkHz = 1.7,
		beats = 2,
		bounce = 0.11,
		sharp = 1,
		skip = 0.3,
		lean = 7,
		nod = 6,
		roll = 4,
		yaw = 3,
		bank = 4,
	},
	-- bunny-like arcs with a short pause between hops; idle like a sitter with the odd hop in place
	hopper = {
		pivot = 0.3,
		breath = 0.016,
		breathPeriod = 2.2,
		breathPitch = 1.2,
		look = 20,
		lookTilt = 8,
		lookEvery = 5.6,
		lookTime = 3,
		sway = 1.2,
		swayPeriod = 4,
		idleHop = 0.07,
		idleHopEvery = 2.8,
		idleHopTime = 0.32,
		idleHopTilt = 6,
		walkHz = 1.5,
		beats = 1,
		duty = 0.62,
		bounce = 0.3,
		sharp = 0.5,
		lean = 5,
		nod = 12,
		roll = 3,
		yaw = 4,
		bank = 4,
	},
	-- golem, dragon, driller: slow and weighty, a stomp and a roll each step; slow breath, rare look round
	heavy = {
		pivot = 0.4,
		breath = 0.008,
		breathPeriod = 4.6,
		breathPitch = 0.6,
		look = 18,
		lookTilt = 2,
		lookEvery = 9,
		lookTime = 5,
		sway = 1,
		swaySide = 0.006,
		swayPeriod = 7,
		walkHz = 1.0,
		beats = 2,
		bounce = 0.02,
		sharp = 1,
		lean = 1.5,
		nod = 0.8,
		roll = 3,
		yaw = 1.5,
		side = 0.01,
		impact = 2.2,
		bank = 2,
		bankMax = 4,
	},
	-- winged and bird pets: hover, a gentle figure-eight bob, bank with turns; fly pitched down when moving
	flyer = {
		hover = 0.3,
		pivot = 0.5,
		breath = 0.035,
		breathPeriod = 2.2,
		breathPitch = 1.5,
		look = 18,
		lookEvery = 7,
		lookTime = 3.4,
		sway = 2,
		swayPeriod = 5.5,
		figure = 0.05,
		figurePeriod = 4.6,
		figureBank = 6,
		walkHz = 1.0,
		beats = 1,
		bounce = 0.06,
		lean = 10,
		nod = 2,
		roll = 4,
		yaw = 2,
		side = 0.02,
		bank = 10,
		bankMax = 25,
	},
	-- ghost, cloud spirit, reaper: a slow sine drift up and down, a soft sway, a slow turn back and forth
	floater = {
		hover = 0.14,
		pivot = 0.5,
		breath = 0.07,
		breathPeriod = 3.6,
		breathPitch = 2,
		sway = 4,
		swaySide = 0.02,
		swayPeriod = 4.7,
		spin = 14,
		spinPeriod = 7.5,
		walkHz = 0.55,
		beats = 1,
		bounce = 0.07,
		lean = 6,
		nod = 3,
		roll = 5,
		yaw = 6,
		side = 0.03,
		bank = 8,
		bankMax = 18,
	},
	-- salamander: a low body that swings side to side when moving; idle raises its head and looks
	slither = {
		pivot = 0.2,
		breath = 0.008,
		breathPeriod = 3.4,
		breathPitch = 0.5,
		look = 16,
		lookRaise = 5,
		lookEvery = 6.5,
		lookTime = 4,
		sway = 0.8,
		swayPeriod = 5,
		walkHz = 1.4,
		beats = 2,
		bounce = 0.012,
		lean = 0,
		nod = 0.6,
		roll = 1.5,
		yaw = 9,
		side = 0.02,
		bank = 2,
	},
	-- slimes and cauldrons: a squash-like bounce made of a small hop, a tilt and a jelly wobble (no scaling)
	blob = {
		pivot = 0,
		breath = 0.01,
		breathPeriod = 2.8,
		breathPitch = 1,
		look = 12,
		lookTilt = 4,
		lookEvery = 6,
		lookTime = 3,
		sway = 2,
		swayPeriod = 3.6,
		idleHop = 0.06,
		idleHopEvery = 3.4,
		idleHopTime = 0.34,
		idleHopTilt = 4,
		wobble = 5,
		wobbleTime = 0.9,
		walkHz = 1.3,
		beats = 1,
		duty = 0.55,
		bounce = 0.15,
		sharp = 0.4,
		lean = 5,
		nod = 8,
		roll = 4,
		yaw = 3,
		bank = 3,
	},
} :: { [string]: { [string]: number } }

-- Every pet: its style, then any fields of its own. `amp` scales the size of all its movements and
-- `speed` how fast they go (both default to 1). Keys are the pet's name in lower case.
PetAnimator.PETS = {
	fox = { style = "sitter" },
	puppy = { style = "sitter", skip = 0.35, yaw = 4 },
	cat = { style = "sitter", lookTilt = 11 },
	bunny = { style = "hopper" },
	penguin = { style = "sitter", bounce = 0.06, skip = 0, roll = 12, yaw = 8, lean = 3, nod = 2, speed = 1.15 },
	turtle = { style = "heavy", bounce = 0.03, roll = 5, yaw = 3.5, look = 22, speed = 0.85 },
	unicorn = { style = "walker", bounce = 0.05, nod = 4 },
	dragon = { style = "heavy" },
	phoenix = { style = "flyer" },
	griffin = { style = "flyer", hover = 0.22 },
	golem = { style = "heavy", amp = 1.1 },
	wolf = { style = "walker" },
	driller = { style = "heavy", roll = 1.5, impact = 1.5, yaw = 1 },
	salamander = { style = "slither" },
	infernobat = { style = "flyer", hover = 0.4, speed = 1.4, figure = 0.07 },
	gargoyle = { style = "flyer", hover = 0.2, speed = 0.8, amp = 0.8 },
	raven = { style = "flyer", hover = 0.28 },
	ghost = { style = "floater" },
	cloudspirit = { style = "floater", hover = 0.1 },
	kingslime = { style = "blob" },
	cauldron = { style = "blob", wobble = 4 },
	drumdevil = { style = "hopper", duty = 0.5, bounce = 0.2, wobble = 5 },
	firedemon = { style = "flyer", hover = 0.18 },
	horneddemon = { style = "walker", speed = 0.8, impact = 1 },
	lavacat = { style = "walker", speed = 1.15, bounce = 0.05, skip = 0.15, lookTilt = 7 },
	plumedlion = { style = "walker", speed = 0.9 },
	reaper = { style = "floater", hover = 0.16, spin = 10 },
	skeletondog = { style = "walker", speed = 1.1, bounce = 0.05, skip = 0.2, lookTilt = 8 },
} :: { [string]: { [string]: any } }

-- Fields that `amp` scales, and the periods that `speed` shortens.
local AMP_FIELDS = {
	"breath",
	"breathPitch",
	"sway",
	"swaySide",
	"figure",
	"figureBank",
	"idleHop",
	"idleHopTilt",
	"wobble",
	"bounce",
	"nod",
	"roll",
	"yaw",
	"side",
	"impact",
}
local PERIOD_FIELDS = {
	"breathPeriod",
	"lookEvery",
	"lookTime",
	"swayPeriod",
	"spinPeriod",
	"figurePeriod",
	"idleHopEvery",
	"idleHopTime",
	"wobbleTime",
}

-- The full profile for a pet name (any case); a style name may be given to use instead of its own.
function PetAnimator.profile(petName: string, styleName: string?): Profile
	local entry = PetAnimator.PETS[string.lower(petName)] or { style = "walker" }
	local style = PetAnimator.STYLES[styleName or entry.style] or PetAnimator.STYLES.walker
	local p = table.clone(DEFAULTS) :: any
	for key, value in style do
		p[key] = value
	end
	for key, value in entry do
		if key ~= "style" and key ~= "amp" and key ~= "speed" then
			p[key] = value
		end
	end
	local amp = entry.amp or 1
	local speed = entry.speed or 1
	for _, key in AMP_FIELDS do
		p[key] *= amp
	end
	for _, key in PERIOD_FIELDS do
		p[key] /= speed
	end
	p.walkHz *= speed
	return p :: Profile
end

local function clamp(x: number, lo: number, hi: number): number
	return if x < lo then lo elseif x > hi then hi else x
end

local function ease(x: number): number
	return x * x * (3 - 2 * x)
end

-- Look-around over u = 0..1: turn left and hold, turn right (a little less) and hold, back to the middle.
local function lookShape(u: number): number
	if u < 0 or u >= 1 then
		return 0
	elseif u < 0.18 then
		return ease(u / 0.18)
	elseif u < 0.45 then
		return 1
	elseif u < 0.63 then
		return 1 - 1.65 * ease((u - 0.45) / 0.18)
	elseif u < 0.85 then
		return -0.65
	end
	return -0.65 * (1 - ease((u - 0.85) / 0.15))
end

-- 1 for the whole look-around, easing in and out at its ends.
local function raiseShape(u: number): number
	if u < 0 or u >= 1 then
		return 0
	end
	return ease(math.min(u / 0.15, 1)) * ease(math.min((1 - u) / 0.15, 1))
end

-- Strides per second at this speed, for a pet this tall.
function PetAnimator.walkHz(p: Profile, height: number, speed: number): number
	local sizeFactor = clamp(math.sqrt(REF_SIZE / math.max(height, 0.1)), 0.5, 1.4)
	local speedFactor = clamp(0.6 + 0.4 * speed / REF_SPEED, 0.6, 1.2)
	return p.walkHz * sizeFactor * speedFactor
end

-- A fresh state for a model of this size; `seed` (0..1) sets where in its motion the pet starts.
function PetAnimator.newState(width: number, height: number, length: number, seed: number): State
	return {
		time = seed * 97,
		cycle = (seed * 7) % 1,
		blend = 0,
		speed = 0,
		turn = 0,
		heading = 0,
		hasHeading = false,
		height = height,
		width = width,
		length = length,
	}
end

-- The pure motion maths: the offset from the pivot's resting place at time t (seconds) and speed
-- (studs per second; Step passes the smoothed speed), given the smoothed blend, walk cycle and
-- turning in `state`.
function PetAnimator.offset(p: Profile, state: State, t: number, speed: number): CFrame
	local h = state.height
	local e = ease(clamp(state.blend, 0, 1))
	local i = 1 - e
	local x, y = 0, p.hover * h
	local pitch, yaw, roll = 0, 0, 0

	-- idle: breathing
	local breathAngle = TAU * t / p.breathPeriod
	y += i * p.breath * h * (0.5 - 0.5 * math.cos(breathAngle))
	pitch += i * p.breathPitch * math.sin(breathAngle)
	-- idle: look round
	local u = (t % p.lookEvery) / p.lookTime
	local look = lookShape(u)
	yaw += i * p.look * look
	roll += i * p.lookTilt * look
	pitch -= i * p.lookRaise * raiseShape(u)
	-- idle: weight shift
	local sway = math.sin(TAU * t / p.swayPeriod)
	roll += i * p.sway * sway
	x += i * p.swaySide * h * sway
	-- idle: slow turn back and forth
	yaw += i * p.spin * math.sin(TAU * t / p.spinPeriod)
	-- idle: figure eight
	local figureAngle = TAU * t / p.figurePeriod
	x += i * p.figure * h * math.sin(figureAngle)
	y += i * p.figure * h * 0.5 * math.sin(2 * figureAngle)
	roll += i * p.figureBank * math.cos(figureAngle)
	-- idle: the odd hop in place, then a wobble
	if p.idleHop > 0 then
		local since = t % p.idleHopEvery
		if since < p.idleHopTime then
			local hx = since / p.idleHopTime
			y += i * p.idleHop * h * math.sin(math.pi * hx)
			pitch -= i * p.idleHopTilt * math.sin(TAU * hx)
		else
			local r = (since - p.idleHopTime) / p.wobbleTime
			if r < 1 then
				roll += i * p.wobble * math.sin(TAU * 1.5 * r) * (1 - r) * (1 - r)
			end
		end
	end

	-- walk
	local amp = e * clamp(0.55 + 0.45 * speed / REF_SPEED, 0.55, 1.15)
	local beatPos = state.cycle * p.beats
	local beat = math.floor(beatPos)
	local bx = beatPos - beat
	local hop, nodShape, wob = 0, 0, 0
	if bx < p.duty then
		local hx = bx / p.duty
		local s = math.sin(math.pi * hx)
		hop = s * s + (s - s * s) * p.sharp
		nodShape = math.sin(TAU * hx)
	else
		local r = (bx - p.duty) / (1 - p.duty)
		wob = math.sin(TAU * 1.5 * r) * (1 - r) * (1 - r)
	end
	hop *= if beat % 2 == 1 then 1 - p.skip else 1 + p.skip
	local swing = math.sin(math.pi * beatPos)
	local impact = (bx / IMPACT_TIME) * math.exp(1 - bx / IMPACT_TIME)
	y += amp * p.bounce * h * hop
	pitch += amp * (p.lean - p.nod * nodShape + p.impact * impact)
	roll += amp * (p.roll * swing + p.wobble * wob)
	yaw += amp * p.yaw * swing
	x += amp * p.side * h * swing

	-- bank into turns
	roll += clamp(state.turn * p.bank, -p.bankMax, p.bankMax)

	-- keep the feet on the floor: lift by however far the lowest corner of the footprint would sink
	local rx, ry, rz = -math.rad(pitch), math.rad(yaw), math.rad(roll)
	local cy = p.pivot * h
	local lowest = y
		+ cy
		- cy * math.cos(rz) * math.cos(rx)
		- math.abs(FOOT * state.width * 0.5 * math.sin(rz) * math.cos(rx))
		- math.abs(FOOT * state.length * 0.5 * math.sin(rx))
	if lowest < 0 then
		y -= lowest
	end
	return CFrame.new(x, y + cy, 0) * CFrame.fromEulerAnglesYXZ(rx, ry, rz) * CFrame.new(0, -cy, 0)
end

-- The model's size around its pivot, measured from its parts.
local function measure(model: Model): (number, number, number)
	local pivot = model:GetPivot()
	local lo = Vector3.new(math.huge, math.huge, math.huge)
	local hi = -lo
	for _, part in model:GetDescendants() do
		if part:IsA("BasePart") then
			local cf = pivot:ToObjectSpace(part.CFrame)
			local half = part.Size / 2
			local reach = Vector3.new(
				math.abs(cf.XVector.X) * half.X + math.abs(cf.YVector.X) * half.Y + math.abs(cf.ZVector.X) * half.Z,
				math.abs(cf.XVector.Y) * half.X + math.abs(cf.YVector.Y) * half.Y + math.abs(cf.ZVector.Y) * half.Z,
				math.abs(cf.XVector.Z) * half.X + math.abs(cf.YVector.Z) * half.Y + math.abs(cf.ZVector.Z) * half.Z
			)
			lo = lo:Min(cf.Position - reach)
			hi = hi:Max(cf.Position + reach)
		end
	end
	if lo.X > hi.X then
		return 2, 2, 2
	end
	local size = hi - lo
	return size.X, math.max(size.Y, hi.Y), size.Z
end

-- An animator for a pet model (a copy the client owns). petName picks the style; it defaults to the
-- model's name.
function PetAnimator.new(model: Model, petName: string?): PetAnimator
	local width, height, length = measure(model)
	local self = setmetatable({
		model = model :: Model?,
		profile = PetAnimator.profile(petName or model.Name),
		state = PetAnimator.newState(width, height, length, math.random()),
	}, PetAnimator)
	return self
end

-- Move the pet for this frame. baseCFrame is where the pet system wants the pet's pivot; speed is
-- how fast the pet is moving, in studs per second.
function PetAnimator.Step(self: PetAnimator, dt: number, baseCFrame: CFrame, speed: number)
	local model = self.model
	if not model then
		return
	end
	local s = self.state
	local step = clamp(dt, 0, 0.1) -- for the smoothing, so a hitch does not snap
	s.time += dt
	s.speed += (speed - s.speed) * (1 - math.exp(-SPEED_RATE * step))
	s.cycle = (s.cycle + dt * PetAnimator.walkHz(self.profile, s.height, s.speed)) % 2
	local target = clamp((speed - WALK_START) / (WALK_FULL - WALK_START), 0, 1)
	s.blend += (target - s.blend) * (1 - math.exp(-BLEND_RATE * step))

	local look = baseCFrame.LookVector
	local heading = math.atan2(-look.X, -look.Z)
	local rate = 0
	if s.hasHeading and dt > 0 then
		local delta = (heading - s.heading + math.pi) % TAU - math.pi
		rate = clamp(delta / dt, -TURN_MAX, TURN_MAX)
	end
	s.heading, s.hasHeading = heading, true
	s.turn += (rate - s.turn) * (1 - math.exp(-TURN_RATE * step))

	model:PivotTo(baseCFrame * PetAnimator.offset(self.profile, s, s.time, s.speed))
end

-- Stop animating. The model is left where it is; destroying it is up to the caller.
function PetAnimator.Destroy(self: PetAnimator)
	self.model = nil
end

return PetAnimator
