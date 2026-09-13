import discord
from discord.ext import commands, tasks
import json
import os
import random
from googletrans import Translator
from datetime import datetime, timedelta

# --- CONFIGURATION INITIALE ---
INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.members = True
INTENTS.reactions = True

bot = commands.Bot(command_prefix="/", intents=INTENTS)
translator = Translator()

DATA_FILE = "quentine_data.json"
SEASON_FILE = "quentine_season.json"

# --- GESTION DE LA BASE DE DONNÉES JSON ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_season_data():
    if not os.path.exists(SEASON_FILE):
        return {"active": False, "start_date": None}
    with open(SEASON_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {"active": False, "start_date": None}

def save_season_data(data):
    with open(SEASON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_user_data(user_id):
    data = load_data()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {
            "pourboires": 100,
            "main_zooba": "Non défini",
            "brigade": "Aucune",
            "victoires_duels": 0,
            "defaites_duels": 0,
            "etoiles_michelin": [],
            "badges_style": [],
            "trophees_debut_saison": 0,
            "trophees_actuels": 0,
            "niveau_cuisine": 1,
            "experience": 0,
            "derniere_activite": datetime.now().isoformat(),
            "total_gains": 0,
            "rang": "Novice",
            "ratio_honneur": 100.0,
            "historique_duels": [],
            "statistiques": {
                "duels_joues": 0,
                "duels_gagnes": 0,
                "duels_perdus": 0,
                "ratio_victoire": 0.0,
                "pourboires_gagnes_total": 0,
                "pourboires_perdus_total": 0
            }
        }
        save_data(data)
    return data[uid]

def update_user_data(user_id, key, value):
    data = load_data()
    uid = str(user_id)
    if uid not in data:
        get_user_data(user_id)
        data = load_data()
    data[uid][key] = value
    save_data(data)

def calculer_rang(victoires):
    """Calcule le rang selon le nombre de victoires"""
    if victoires < 10:
        return "Novice"
    elif victoires < 25:
        return "Apprenti"
    elif victoires < 50:
        return "Chef"
    elif victoires < 100:
        return "Maître Chef"
    elif victoires < 150:
        return "Grand Chef"
    else:
        return "Légende"

@bot.event
async def on_ready():
    print(f"🍽️ Le chef {bot.user.name} est en cuisine et prêt à servir !")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Commandes Slash synchronisées : {len(synced)}")
    except Exception as e:
        print(f"❌ Erreur : {e}")
    
    if not update_classement_automatique.is_running():
        update_classement_automatique.start()


# --- TRADUCTION INVISIBLE AUTOMATIQUE ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    u_data = get_user_data(message.author.id)
    u_data["derniere_activite"] = datetime.now().isoformat()
    data = load_data()
    data[str(message.author.id)] = u_data
    save_data(data)

    try:
        detected = translator.detect(message.content)
        if detected.lang != 'fr' and len(message.content) > 3:
            await message.add_reaction("🌐")
    except Exception:
        pass
        
    await bot.process_commands(message)

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    if reaction.emoji == "🌐":
        message = reaction.message
        try:
            translation = translator.translate(message.content, dest='fr')
            embed = discord.Embed(
                title="🌐 Traduction en Cuisine",
                description=f"**Message original ({message.author.display_name}) :**\n{message.content}\n\n**Traduction française :**\n{translation.text}",
                color=discord.Color.blue()
            )
            await user.send(embed=embed)
        except Exception:
            pass


# --- 1. CHOIX DE BRIGADE ---
class BrigadeSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="La Brigade des Viandes 🥩", description="Tanks (Bruce, Duke, Buck...)", value="La Brigade des Viandes 🥩"),
            discord.SelectOption(label="Les Chefs Poissonniers 🐟", description="DPS/Assassins (Nix, Jade, Steve...)", value="Les Chefs Poissonniers 🐟"),
            discord.SelectOption(label="Les Maîtres Sauciers 🧪", description="Supports (Fuzzy, Larry, Pepper...)", value="Les Maîtres Sauciers 🧪")
        ]
        super().__init__(placeholder="Choisissez votre brigade...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        update_user_data(interaction.user.id, "brigade", self.values[0])
        await interaction.response.send_message(f"✅ Brigade assignée : **{self.values[0]}** !", ephemeral=True)

class BrigadeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(BrigadeSelect())

@bot.tree.command(name="quentine_choix_brigade", description="Affiche le menu de sélection de votre brigade.")
async def quentine_choix_brigade(interaction: discord.Interaction):
    view = BrigadeView()
    embed = discord.Embed(
        title="🍽️ Choix de votre Brigade - La Quentine",
        description="Sélectionnez votre rôle principal !",
        color=discord.Color.orange()
    )
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# --- 2. CHOIX ANIMAL ZOOBA ---
ANIMAUX_ZOOBA = ["Bruce 🦍", "Nix 🦊", "Duke 🦁", "Buck 🦌", "Fuzzy 🐨", "Larry 🦒", "Pepper 🦝", "Jade 🐍", "Steve 🦈", "Shelly 🐢"]

class AnimalSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=animal, value=animal) for animal in ANIMAUX_ZOOBA]
        super().__init__(placeholder="Choisissez votre animal principal...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        update_user_data(interaction.user.id, "main_zooba", self.values[0])
        await interaction.response.send_message(f"✅ Animal principal : **{self.values[0]}** !", ephemeral=True)

class AnimalView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(AnimalSelect())

@bot.tree.command(name="quentine_set_main", description="Choisir votre animal principal Zooba.")
async def quentine_set_main(interaction: discord.Interaction):
    view = AnimalView()
    embed = discord.Embed(title="🐾 Choix de votre Main Zooba", description="Sélectionnez votre animal préféré !", color=discord.Color.green())
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# --- 3. COMMANDE PROFIL ---
@bot.tree.command(name="quentine_carte", description="Affiche votre profil complet.")
async def quentine_carte(interaction: discord.Interaction, membre: discord.Member = None):
    target = membre or interaction.user
    u_data = get_user_data(target.id)

    rang_emoji = "🔰" if u_data["rang"] == "Novice" else "🟨" if u_data["rang"] == "Apprenti" else "🟩" if u_data["rang"] == "Chef" else "🔵" if u_data["rang"] == "Maître Chef" else "👑" if u_data["rang"] == "Grand Chef" else "⭐"

    embed = discord.Embed(
        title=f"📋 Carte de Cuisine - {target.display_name}",
        color=discord.Color.gold()
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    
    embed.add_field(name="🪙 Pourboires", value=f"`{u_data['pourboires']} 🪙`", inline=True)
    embed.add_field(name="🛡️ Brigade", value=f"`{u_data['brigade']}`", inline=True)
    embed.add_field(name=f"{rang_emoji} Rang", value=f"`{u_data['rang']}`", inline=True)
    
    embed.add_field(name="🐾 Animal Main", value=f"`{u_data['main_zooba']}`", inline=True)
    embed.add_field(name="⚔️ Duels Gagnés", value=f"`{u_data['victoires_duels']}`", inline=True)
    embed.add_field(name="📊 Ratio Victoire", value=f"`{u_data['statistiques']['ratio_victoire']:.1f}%`", inline=True)
    
    embed.add_field(name="⭐ Niveau Cuisine", value=f"`Niveau {u_data['niveau_cuisine']} | {u_data['experience']} XP`", inline=False)
    
    badges = " ".join(u_data['badges_style']) if u_data['badges_style'] else "Aucun badge"
    embed.add_field(name="✨ Badges", value=badges, inline=False)

    await interaction.response.send_message(embed=embed)


# --- 4. SYSTÈME DE DUELS ---
LISTE_DEFIS = [
    "🔥 Le Défi Flambé : Faire un Top 1 avec Larry sans utiliser de trousse.",
    "⚡ Le Défi Épicé : Faire 3 kills en zone de feu/gaz.",
    "🎯 Le Défi Allégé : Gagner en ramassant uniquement des armes communes.",
    "💣 Le Défi du Chef : Assommer 3 adversaires avec des éléments du décor.",
    "🛡️ Le Défi Tartare : Encaisser 5000+ dégâts sans mourir en tant que tank.",
    "⚡ Le Défi Éclair : Faire un Top 1 en moins de 5 minutes.",
    "🎪 Le Défi Acrobate : Faire 5 kills sans se faire toucher.",
    "🧠 Le Défi Stratège : Gagner sans utiliser un seul consommable."
]

class DuelButtonView(discord.ui.View):
    def __init__(self, challenger: discord.User, opponent: discord.User, mise: int):
        super().__init__(timeout=3600)
        self.challenger = challenger
        self.opponent = opponent
        self.mise = mise
        self.completed = False

    @discord.ui.button(label="J'ai fini mon plat ! 🍳", style=discord.ButtonStyle.green)
    async def finish_dish(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in (self.challenger, self.opponent):
            await interaction.response.send_message("❌ Ce n'est pas votre duel !", ephemeral=True)
            return

        if self.completed:
            await interaction.response.send_message("❌ Ce duel est déjà terminé !", ephemeral=True)
            return

        winner = interaction.user
        loser = self.opponent if winner == self.challenger else self.challenger

        w_data = get_user_data(winner.id)
        l_data = get_user_data(loser.id)

        # Vérifier solde
        if l_data["pourboires"] < self.mise:
            self.mise = l_data["pourboires"]

        # Transférer pourboires
        w_data["pourboires"] += self.mise
        l_data["pourboires"] -= self.mise
        
        # Statistiques
        w_data["victoires_duels"] += 1
        w_data["statistiques"]["duels_gagnes"] += 1
        w_data["statistiques"]["duels_joues"] += 1
        w_data["statistiques"]["pourboires_gagnes_total"] += self.mise
        w_data["experience"] += 50
        w_data["total_gains"] += self.mise
        w_data["rang"] = calculer_rang(w_data["victoires_duels"])
        
        l_data["defaites_duels"] += 1
        l_data["statistiques"]["duels_perdus"] += 1
        l_data["statistiques"]["duels_joues"] += 1
        l_data["statistiques"]["pourboires_perdus_total"] += self.mise
        l_data["experience"] += 20
        l_data["rang"] = calculer_rang(l_data["victoires_duels"])

        # Calculer ratios
        if w_data["statistiques"]["duels_joues"] > 0:
            w_data["statistiques"]["ratio_victoire"] = (w_data["statistiques"]["duels_gagnes"] / w_data["statistiques"]["duels_joues"]) * 100
        if l_data["statistiques"]["duels_joues"] > 0:
            l_data["statistiques"]["ratio_victoire"] = (l_data["statistiques"]["duels_gagnes"] / l_data["statistiques"]["duels_joues"]) * 100

        # Gestion du niveau
        if w_data["experience"] >= w_data["niveau_cuisine"] * 100:
            w_data["niveau_cuisine"] += 1
            w_data["badges_style"].append(f"🎖️ Chef Niveau {w_data['niveau_cuisine']}")

        # Sauvegarder
        data = load_data()
        data[str(winner.id)] = w_data
        data[str(loser.id)] = l_data
        save_data(data)

        embed = discord.Embed(
            title="🏆 Service Terminé - Vainqueur !",
            description=f"**{winner.mention}** remporte **{self.mise} Pourboires 🪙** !\n\n📊 Nouveau rang : **{w_data['rang']}**\n✨ +50 XP",
            color=discord.Color.green()
        )
        
        for child in self.children:
            child.disabled = True
        
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message(f"✅ Victoire validée ! Bien joué chef ! 👨‍🍳", ephemeral=True)
        
        self.completed = True
        self.stop()

@bot.tree.command(name="quentine_duel", description="Défie un autre membre en duel culinaire !")
async def quentine_duel(interaction: discord.Interaction, opponent: discord.Member, mise: int):
    if opponent == interaction.user:
        await interaction.response.send_message("❌ Vous ne pouvez pas cuisiner contre vous-même !", ephemeral=True)
        return

    if opponent.bot:
        await interaction.response.send_message("❌ Vous ne pouvez pas défier un bot !", ephemeral=True)
        return

    c_data = get_user_data(interaction.user.id)
    if c_data["pourboires"] < mise:
        await interaction.response.send_message(f"❌ Vous n'avez pas assez de Pourboires ! (Il vous manque {mise - c_data['pourboires']})", ephemeral=True)
        return

    if mise < 10:
        await interaction.response.send_message("❌ La mise minimale est 10 Pourboires !", ephemeral=True)
        return

    defi_choisi = random.choice(LISTE_DEFIS)
    embed = discord.Embed(
        title="⚔️ DUEL LANCÉ !",
        description=f"**{interaction.user.mention}** défie **{opponent.mention}** !\n\n**Mise :** {mise} Pourboires 🪙\n\n🎯 **DÉFI :**\n{defi_choisi}\n\n*Postez votre preuve dans #degustation-replays et cliquez quand c'est fait !*",
        color=discord.Color.red()
    )
    view = DuelButtonView(interaction.user, opponent, mise)
    await interaction.response.send_message(embed=embed, view=view)


# --- 5. SYSTÈME DE SAISONS ---
@bot.tree.command(name="quentine_saison_ouvrir", description="[Admin] Ouvre une nouvelle saison.")
async def quentine_saison_ouvrir(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin seulement !", ephemeral=True)
        return

    data = load_data()
    season_data = load_season_data()
    
    for uid in data:
        data[uid]["trophees_debut_saison"] = data[uid]["trophees_actuels"]
    
    season_data["active"] = True
    season_data["start_date"] = datetime.now().isoformat()
    
    save_data(data)
    save_season_data(season_data)

    embed = discord.Embed(
        title="🗓️ Nouvelle Saison Ouverte !",
        description="🔥 Les compteurs sont étalonnés. Que la course aux étoiles commence !",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="quentine_saison_classement", description="Affiche le classement saisonnier en direct.")
async def quentine_saison_classement(interaction: discord.Interaction):
    data = load_data()
    season_data = load_season_data()
    
    if not season_data.get("active", False):
        await interaction.response.send_message("❌ Aucune saison active actuellement.", ephemeral=True)
        return
    
    if not data:
        await interaction.response.send_message("❌ Aucune donnée.", ephemeral=True)
        return

    classement = []
    for uid, u_info in data.items():
        progression = u_info["trophees_actuels"] - u_info["trophees_debut_saison"]
        duels_gagnes = u_info.get("victoires_duels", 0)
        classement.append((uid, progression, u_info["trophees_actuels"], duels_gagnes))

    classement.sort(key=lambda x: x[1], reverse=True)

    embed = discord.Embed(title="🏆 Classement Saisonnier", color=discord.Color.gold())
    
    description = ""
    for index, (uid, prog, actuels, duels) in enumerate(classement[:15], start=1):
        member = interaction.guild.get_member(int(uid))
        name = member.display_name if member else f"Cuisinier #{uid}"
        medal = "🥇" if index == 1 else "🥈" if index == 2 else "🥉" if index == 3 else f"#{index}"
        description += f"{medal} **{name}** — `+{prog}` 🏆 | Duels : `{duels}` ⚔️\n"

    embed.description = description if description else "Pas de données."
    embed.set_footer(text="Top 3 récompensés à la fin de la saison !")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="quentine_saison_cloture", description="[Admin] Clôture la saison et récompense le Top 3.")
async def quentine_saison_cloture(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin seulement !", ephemeral=True)
        return

    data = load_data()
    season_data = load_season_data()
    classement = []
    
    for uid, u_info in data.items():
        progression = u_info["trophees_actuels"] - u_info["trophees_debut_saison"]
        classement.append((uid, progression))

    classement.sort(key=lambda x: x[1], reverse=True)

    if not classement:
        await interaction.response.send_message("❌ Personne à récompenser.", ephemeral=True)
        return

    recompenses = [10000, 5000, 2500]
    resultats_texte = "🎯 **Résultats de la Clôture de Saison :**\n\n"

    for i in range(min(3, len(classement))):
        uid, prog = classement[i]
        member = interaction.guild.get_member(int(uid))
        if member:
            prime = recompenses[i]
            data[uid]["pourboires"] += prime
            data[uid]["total_gains"] += prime
            
            if i == 0:
                data[uid]["badges_style"].append("👑 Grand Chef de Saison")
                data[uid]["etoiles_michelin"].append("⭐ Grand Chef de Saison")
                caviar_role = discord.utils.get(interaction.guild.roles, name="Caviar 💎")
                if caviar_role:
                    try:
                        await member.add_roles(caviar_role)
                    except:
                        pass
            elif i == 1:
                data[uid]["badges_style"].append("🥈 Sous Chef de Saison")
                data[uid]["etoiles_michelin"].append("⭐ Sous Chef de Saison")
            else:
                data[uid]["badges_style"].append("🥉 Chef de Partie de Saison")
                data[uid]["etoiles_michelin"].append("⭐ Chef de Partie de Saison")
            
            resultats_texte += f"**Rang #{i+1}** : {member.mention}\n├─ Progression : `+{prog}` 🏆\n├─ Prime : **{prime} Pourboires 🪙**\n└─ Badge : ⭐ Étoile Michelin\n\n"

    season_data["active"] = False
    save_data(data)
    save_season_data(season_data)
    
    embed = discord.Embed(title="🛎️ Fin de Saison !", description=resultats_texte, color=discord.Color.purple())
    await interaction.response.send_message(embed=embed)


# --- 6. SYSTÈME DE SHOP ---
SHOP_ITEMS = {
    "1": {"nom": "Costume Chef Premium", "prix": 500, "emoji": "👨‍🍳"},
    "2": {"nom": "Auréole Dorée", "prix": 300, "emoji": "✨"},
    "3": {"nom": "Trophée Miniature", "prix": 250, "emoji": "🏆"},
    "4": {"nom": "Parchemin Secret", "prix": 400, "emoji": "📜"},
    "5": {"nom": "Cristal Enchanté", "prix": 1000, "emoji": "💎"}
}

@bot.tree.command(name="quentine_shop", description="Accédez à la boutique !")
async def quentine_shop(interaction: discord.Interaction):
    u_data = get_user_data(interaction.user.id)
    
    embed = discord.Embed(title="🛍️ Boutique Culinaire", color=discord.Color.purple())
    embed.add_field(name="💰 Solde", value=f"`{u_data['pourboires']} 🪙`", inline=False)
    
    shop_text = ""
    for key, item in SHOP_ITEMS.items():
        shop_text += f"**{key}.** {item['emoji']} {item['nom']} — `{item['prix']} 🪙`\n"
    
    embed.add_field(name="📦 Articles", value=shop_text, inline=False)
    embed.set_footer(text="Utilisez /quentine_acheter <numero>")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="quentine_acheter", description="Acheter un item en boutique.")
async def quentine_acheter(interaction: discord.Interaction, numero: str):
    if numero not in SHOP_ITEMS:
        await interaction.response.send_message("❌ Numéro invalide.", ephemeral=True)
        return
    
    item = SHOP_ITEMS[numero]
    u_data = get_user_data(interaction.user.id)
    
    if u_data["pourboires"] < item["prix"]:
        manque = item["prix"] - u_data["pourboires"]
        await interaction.response.send_message(f"❌ Il vous manque {manque} 🪙", ephemeral=True)
        return
    
    u_data["pourboires"] -= item["prix"]
    u_data["badges_style"].append(f"{item['emoji']} {item['nom']}")
    update_user_data(interaction.user.id, "pourboires", u_data["pourboires"])
    update_user_data(interaction.user.id, "badges_style", u_data["badges_style"])
    
    embed = discord.Embed(
        title="✅ Achat Réussi !",
        description=f"Vous avez acheté : **{item['emoji']} {item['nom']}**\n\nSolde : `{u_data['pourboires']} 🪙`",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# --- 7. RECRUTEMENT ---
class CandidatureModal(discord.ui.Modal, title="Candidature - La Quentine"):
    zooba_id = discord.ui.TextInput(label="Pseudo Zooba", placeholder="Ex: Pseudo#1234", required=True)
    trophees = discord.ui.TextInput(label="Nombre de trophées", placeholder="Ex: 15000", required=True)
    presentation = discord.ui.TextInput(label="Présentation", placeholder="Dites-nous qui vous êtes !", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        surveillance_channel = discord.utils.get(guild.text_channels, name="surveillance-hygiene")
        
        embed = discord.Embed(title="🕵️ Nouveau Candidat", color=discord.Color.purple())
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="Candidat", value=interaction.user.mention, inline=False)
        embed.add_field(name="Pseudo Zooba", value=self.zooba_id.value, inline=True)
        embed.add_field(name="Trophées", value=self.trophees.value, inline=True)
        embed.add_field(name="Présentation", value=self.presentation.value, inline=False)

        view = RecrutementActionView(interaction.user.id)
        if surveillance_channel:
            await surveillance_channel.send(embed=embed, view=view)
            await interaction.response.send_message("✅ Candidature transmise au staff !", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Erreur : salon introuvable.", ephemeral=True)

class RecrutementActionView(discord.ui.View):
    def __init__(self, candidate_id: int):
        super().__init__(timeout=None)
        self.candidate_id = candidate_id

    @discord.ui.button(label="Embaucher 🟢", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = guild.get_member(self.candidate_id)
        if member:
            get_user_data(member.id)  # Crée le profil
            await interaction.message.edit(content=f"✅ Accepté par {interaction.user.mention}", view=None)
            try:
                await member.send("🎉 Bienvenue dans LA QUENTINE !")
            except:
                pass

    @discord.ui.button(label="Recaler 🔴", style=discord.ButtonStyle.red)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.edit(content=f"❌ Refusé par {interaction.user.mention}", view=None)

@bot.tree.command(name="quentine_menu_recrutement", description="[Admin] Affiche le menu de recrutement.")
async def quentine_menu_recrutement(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin seulement !", ephemeral=True)
        return

    class OpenModalButton(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(label="Postuler à la Brigade 🍳", style=discord.ButtonStyle.blurple)
        async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_modal(CandidatureModal())

    embed = discord.Embed(
        title="🚪 Recrutement - LA QUENTINE",
        description="Cliquez pour postuler à la brigade !",
        color=discord.Color.orange()
    )
    await interaction.channel.send(embed=embed, view=OpenModalButton())
    await interaction.response.send_message("✅ Panneau déployé !", ephemeral=True)


# --- 8. COMMANDES ADMIN ---
@bot.tree.command(name="quentine_admin_donner_pourboires", description="[Admin] Donner des pourboires.")
async def quentine_admin_donner_pourboires(interaction: discord.Interaction, membre: discord.Member, montant: int):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin seulement !", ephemeral=True)
        return
    
    u_data = get_user_data(membre.id)
    u_data["pourboires"] += montant
    update_user_data(membre.id, "pourboires", u_data["pourboires"])
    
    embed = discord.Embed(
        title="💰 Distribution",
        description=f"{membre.mention} reçoit **{montant} Pourboires 🪙**\n\nNouveau solde : `{u_data['pourboires']} 🪙`",
        color=discord.Color.gold()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="quentine_admin_reset_user", description="[Admin] Réinitialiser un joueur.")
async def quentine_admin_reset_user(interaction: discord.Interaction, membre: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin seulement !", ephemeral=True)
        return
    
    data = load_data()
    uid = str(membre.id)
    data[uid] = {
        "pourboires": 100,
        "main_zooba": "Non défini",
        "brigade": "Aucune",
        "victoires_duels": 0,
        "defaites_duels": 0,
        "etoiles_michelin": [],
        "badges_style": [],
        "trophees_debut_saison": 0,
        "trophees_actuels": 0,
        "niveau_cuisine": 1,
        "experience": 0,
        "derniere_activite": datetime.now().isoformat(),
        "total_gains": 0,
        "rang": "Novice",
        "ratio_honneur": 100.0,
        "historique_duels": [],
        "statistiques": {
            "duels_joues": 0,
            "duels_gagnes": 0,
            "duels_perdus": 0,
            "ratio_victoire": 0.0,
            "pourboires_gagnes_total": 0,
            "pourboires_perdus_total": 0
        }
    }
    save_data(data)
    
    await interaction.response.send_message(f"✅ {membre.mention} réinitialisé !", ephemeral=True)

@bot.tree.command(name="quentine_stats_clan", description="[Admin] Affiche les stats globales du clan.")
async def quentine_stats_clan(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin seulement !", ephemeral=True)
        return
    
    data = load_data()
    
    total_membres = len(data)
    total_pourboires = sum(u["pourboires"] for u in data.values())
    total_gains = sum(u.get("total_gains", 0) for u in data.values())
    total_duels = sum(u["victoires_duels"] for u in data.values())
    total_duels_joues = sum(u["statistiques"]["duels_joues"] for u in data.values())
    
    embed = discord.Embed(title="📊 Stats Globales - LA QUENTINE", color=discord.Color.blue())
    embed.add_field(name="👥 Membres", value=f"`{total_membres}`", inline=True)
    embed.add_field(name="🪙 Pourboires", value=f"`{total_pourboires}`", inline=True)
    embed.add_field(name="💰 Gains Total", value=f"`{total_gains}`", inline=True)
    embed.add_field(name="⚔️ Duels Gagnés", value=f"`{total_duels}`", inline=True)
    embed.add_field(name="📈 Duels Joués", value=f"`{total_duels_joues}`", inline=True)
    
    await interaction.response.send_message(embed=embed)


# --- 9. AIDE ---
@bot.tree.command(name="quentine_aide", description="Affiche toutes les commandes.")
async def quentine_aide(interaction: discord.Interaction):
    embed = discord.Embed(title="📚 Guide - LA QUENTINE", color=discord.Color.orange())
    
    embed.add_field(
        name="👤 Profil",
        value="`/quentine_set_main` - Choisir animal\n`/quentine_choix_brigade` - Choisir brigade\n`/quentine_carte` - Voir profil",
        inline=False
    )
    
    embed.add_field(
        name="⚔️ Duels",
        value="`/quentine_duel @joueur [mise]` - Lancer un duel",
        inline=False
    )
    
    embed.add_field(
        name="🏆 Saisons",
        value="`/quentine_saison_classement` - Voir classement\n`/quentine_saison_ouvrir` - Ouvrir saison (Admin)\n`/quentine_saison_cloture` - Clôturer saison (Admin)",
        inline=False
    )
    
    embed.add_field(
        name="🛍️ Boutique",
        value="`/quentine_shop` - Voir boutique\n`/quentine_acheter <numero>` - Acheter item",
        inline=False
    )
    
    embed.add_field(
        name="⚙️ Admin",
        value="`/quentine_menu_recrutement` - Menu recrutement\n`/quentine_admin_donner_pourboires` - Donner pourboires\n`/quentine_stats_clan` - Stats clan",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


# --- 10. TÂCHE AUTOMATIQUE ---
@tasks.loop(hours=24)
async def update_classement_automatique():
    # Placeholder pour mise à jour quotidienne
    pass


# LANCEMENT
bot.run("mets_ton_token_discord_ici")
