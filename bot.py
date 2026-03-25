import discord
from discord.ext import commands
from discord import app_commands
import aiohttp, os

BOT_TOKEN     = os.environ['BOT_TOKEN']
SERVER_URL    = 'https://n5auth.onrender.com'
GUILD_ID      = 1476431914851369044
REQUIRED_ROLE = 1486212366017237063

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)
tree = bot.tree

def has_role(member): return any(r.id == REQUIRED_ROLE for r in member.roles)

async def api(method, path, body=None):
    async with aiohttp.ClientSession() as s:
        fn = s.post if method == 'POST' else s.get
        kw = {'headers': {'X-Bot-Token': BOT_TOKEN}}
        if body: kw['json'] = body
        async with fn(SERVER_URL + path, **kw) as r:
            return await r.json()


@tree.command(name='link-device', description='Link your Quest to your Discord using the 6-digit code',
              guild=discord.Object(id=GUILD_ID))
@app_commands.describe(code='The 6-digit code shown in the Meta browser')
async def link_device(interaction: discord.Interaction, code: str):
    await interaction.response.defer(ephemeral=True)
    if not has_role(interaction.user):
        await interaction.followup.send('You need the required role.', ephemeral=True); return
    if len(code) != 6 or not code.isdigit():
        await interaction.followup.send('Code must be 6 digits.', ephemeral=True); return

    resp = await api('POST', '/bot-link', {'code': code, 'discord_id': str(interaction.user.id)})

    if resp.get('ok'):
        await interaction.followup.send('Device linked! Relaunch Animal Company.', ephemeral=True)
    elif resp.get('reason') == 'invalid_code':
        await interaction.followup.send('Code not found. Copy it carefully.', ephemeral=True)
    elif resp.get('reason') == 'expired':
        await interaction.followup.send('Code expired. Relaunch the game for a new one.', ephemeral=True)
    elif resp.get('reason') == 'already_linked':
        await interaction.followup.send('You already have a device linked. Use /change-device.', ephemeral=True)
    else:
        await interaction.followup.send(f'Error: {resp}', ephemeral=True)


@tree.command(name='change-device', description='Switch your linked device to a new one',
              guild=discord.Object(id=GUILD_ID))
@app_commands.describe(new_code='6-digit code from your new device')
async def change_device(interaction: discord.Interaction, new_code: str):
    await interaction.response.defer(ephemeral=True)
    if not has_role(interaction.user):
        await interaction.followup.send('You need the required role.', ephemeral=True); return
    if len(new_code) != 6 or not new_code.isdigit():
        await interaction.followup.send('Code must be 6 digits.', ephemeral=True); return

    link = await api('POST', '/bot-link', {'code': new_code, 'discord_id': '__temp__'})
    if link.get('reason') == 'invalid_code':
        await interaction.followup.send('Code not found. Open the game on your new device first.', ephemeral=True); return
    if link.get('reason') == 'expired':
        await interaction.followup.send('Code expired. Relaunch the game on your new device.', ephemeral=True); return

    new_hwid = link.get('hwid', new_code)
    resp = await api('POST', '/bot-change', {'discord_id': str(interaction.user.id), 'new_hwid': new_hwid})

    if resp.get('ok'):
        await interaction.followup.send('Device changed! Relaunch on your new device.', ephemeral=True)
    elif resp.get('reason') == 'no_linked_device':
        await interaction.followup.send('No linked device. Use /link-device first.', ephemeral=True)
    else:
        await interaction.followup.send(f'Error: {resp}', ephemeral=True)


@bot.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f'Ready as {bot.user}')

bot.run(BOT_TOKEN)
